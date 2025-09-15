import asyncio
import json
import logging
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
from aiortc.contrib.media import MediaPlayer, MediaRelay
import sounddevice as sd
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

relay = MediaRelay()
peer_connections = {}

def create_rtc_config():
    return RTCConfiguration([
        RTCIceServer("stun:stun.l.google.com:19302"),
        RTCIceServer("stun:stun1.l.google.com:19302")
    ])

async def create_local_tracks():
    try:
        player = MediaPlayer("/dev/null", format="alsa", options={
            "channels": "1",
            "sample_rate": "44100"
        })
        return player.audio
    except Exception as e:
        logger.error(f"Failed to create local audio track: {e}")
        return None

def handle_offer(offer_sdp, session_id):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(_handle_offer_async(offer_sdp, session_id))
        return result
    except Exception as e:
        logger.error(f"Error in handle_offer: {e}")
        return None
    finally:
        if loop:
            loop.close()

async def _handle_offer_async(offer_sdp, session_id):
    try:
        pc = RTCPeerConnection(create_rtc_config())
        peer_connections[session_id] = pc
        
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"Connection state: {pc.connectionState}")
            if pc.connectionState == "closed":
                if session_id in peer_connections:
                    del peer_connections[session_id]
        
        @pc.on("track")
        async def on_track(track):
            logger.info(f"Received track: {track.kind}")
            if track.kind == "audio":
                relay.subscribe(track)
        
        local_audio = await create_local_tracks()
        if local_audio:
            pc.addTrack(local_audio)
        
        offer = RTCSessionDescription(sdp=offer_sdp, type="offer")
        await pc.setRemoteDescription(offer)
        
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        return answer.sdp
        
    except Exception as e:
        logger.error(f"Error creating WebRTC answer: {e}")
        return None

def cleanup_connection(session_id):
    if session_id in peer_connections:
        try:
            pc = peer_connections[session_id]
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(pc.close())
            del peer_connections[session_id]
            logger.info(f"Cleaned up connection for session {session_id}")
        except Exception as e:
            logger.error(f"Error cleaning up connection: {e}")
        finally:
            if loop:
                loop.close()

def get_active_connections():
    return len(peer_connections)