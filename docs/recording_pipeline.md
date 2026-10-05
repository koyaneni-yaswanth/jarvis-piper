# Demonstration Recording Pipeline

The JARVIS-PiPER recording pipeline is engineered to record high-throughput multi-modal interactions with zero frame drops and resilience to sudden system interrupts.

---

## 1. Lifecycle and State Machine

The recorder node (`jarvis_piper_recorder`) operates under an explicit finite state machine:

```
  ┌──────────────┐      StartEpisode(task, operator)      ┌──────────────┐
  │     IDLE     ├───────────────────────────────────────►│  RECORDING   │
  └──────────────┘                                        └──────┬───────┘
         ▲                                                       │
         │                StopEpisode(success, discard)          │
         └───────────────────────────────────────────────────────┘
```

1. **IDLE**: The node subscribes to `/jarvis_piper/sync/frame` and verifies sensor freshness.
2. **RECORDING**: Each synchronized frame is written to an in-memory queue. Worker threads immediately append serialized JSON records to `stream_journal.jsonl` and append video frames to the video encoder.
3. **FINALIZING**: Upon receiving `StopEpisode`, the node flushes file buffers, writes `trajectory.json`, compiles `metadata.json`, and triggers the asynchronous quality audit.

---

## 2. Crash-Proof Journal (`stream_journal.jsonl`)

Traditional single-file formats (such as unfinalized HDF5 or monolithic JSON) risk total data corruption if power is lost mid-recording. 
JARVIS-PiPER uses line-delimited JSON (`stream_journal.jsonl`). Each frame is an independent, valid JSON object flushed to disk immediately. Even if power cuts out during a 10-minute demonstration, all elapsed seconds remain 100% recoverable.

---

## 3. Remote Control Services

The recorder exposes ROS 2 services for automated or operator-triggered data collection:
- `/jarvis_piper/recorder/start_episode` (`StartEpisode.srv`)
- `/jarvis_piper/recorder/stop_episode` (`StopEpisode.srv`)
- `/jarvis_piper/recorder/discard_episode` (`DiscardEpisode.srv`)
- `/jarvis_piper/recorder/get_status` (`GetRecorderStatus.srv`)
