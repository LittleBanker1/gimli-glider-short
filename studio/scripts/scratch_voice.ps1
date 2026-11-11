# Scratch voice: Windows SAPI TTS -> voice.wav (48 kHz mono 16-bit) + raw word starts (words_raw.json).
# Usage: powershell -File scripts/scratch_voice.ps1 <SCRIPT.md> <outDir> [voiceName] [rate]
param([string]$Script, [string]$Out, [string]$Voice = "Microsoft David Desktop", [int]$Rate = 0)
Add-Type -AssemblyName System.Speech
$lines = Get-Content $Script -Encoding UTF8 | Where-Object { $_ -match '^\d+\. ' } | ForEach-Object { ($_ -replace '^\d+\. ', '') -replace '\s*\*\([^)]*\)\*', '' }
$esc = { param($t) [System.Security.SecurityElement]::Escape($t) }
$body = ($lines | ForEach-Object { (& $esc $_) -replace '…', '<break time="550ms"/>' -replace ' — ', ', ' }) -join '<break time="420ms"/>'
$ssml = "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'><break time='120ms'/>$body<break time='600ms'/></speak>"
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice($Voice); $s.Rate = $Rate
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(48000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$s.SetOutputToWaveFile((Join-Path $Out "voice.wav"), $fmt)
$words = New-Object System.Collections.ArrayList
Register-ObjectEvent -InputObject $s -EventName SpeakProgress -SourceIdentifier sp -Action { [void]$Event.MessageData.Add(@{ w = $EventArgs.Text; s = $EventArgs.AudioPosition.TotalSeconds }) } -MessageData $words | Out-Null
$s.SpeakSsml($ssml)
Start-Sleep -Milliseconds 300
Unregister-Event sp; $s.Dispose()
$words | ConvertTo-Json -Compress | Set-Content (Join-Path $Out "words_raw.json") -Encoding utf8
"words: $($words.Count)"
