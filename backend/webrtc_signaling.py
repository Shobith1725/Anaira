# backend/webrtc_signaling.py
# pip install aiortc

from fastapi import APIRouter
from pydantic import BaseModel
from aiortc import RTCPeerConnection, RTCSessionDescription
from webrtc_peer import ANAIRAAudioTrack

router = APIRouter(tags=["webrtc"])

# Keep references alive so peers aren't garbage-collected mid-call
_peers: set[RTCPeerConnection] = set()


class SDPPayload(BaseModel):
    sdp: str
    type: str


@router.post("/rtc/offer")
async def rtc_offer(payload: SDPPayload):
    pc = RTCPeerConnection()
    _peers.add(pc)

    @pc.on("connectionstatechange")
    async def on_state():
        print(f"[WebRTC] peer state → {pc.connectionState}")
        if pc.connectionState in ("failed", "closed"):
            _peers.discard(pc)

    # Data channel for sending JSON events back to frontend (tool_call, session, done, etc.)
    channel = pc.createDataChannel("control")

    @pc.on("track")
    async def on_track(track):
        if track.kind == "audio":
            print("[WebRTC] audio track received from browser")
            tts_track = ANAIRAAudioTrack(track, channel)
            pc.addTrack(tts_track)

    offer = RTCSessionDescription(sdp=payload.sdp, type=payload.type)
    await pc.setRemoteDescription(offer)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}