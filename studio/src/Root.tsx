import React from "react";
import { Composition } from "remotion";
import { BridgeShort, BRIDGE_FRAMES } from "./videos/bridge/Bridge";
import { GimliShort, GIMLI_FRAMES } from "./videos/gimli/Gimli";

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="BridgeShort" component={BridgeShort} durationInFrames={BRIDGE_FRAMES} fps={30} width={1080} height={1920} />
    <Composition id="GimliShort" component={GimliShort} durationInFrames={GIMLI_FRAMES} fps={30} width={1080} height={1920} />
  </>
);
