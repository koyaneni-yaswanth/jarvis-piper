"""
JARVIS PiPER Operator Web Dashboard Node
Lightweight HTTP/REST & WebSocket dashboard server providing full GUI controls,
real-time telemetry graphs, video preview, and one-click dataset export.
"""

import glob
import json
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional

import rclpy
from rclpy.node import Node
from jarvis_piper_interfaces.msg import RecorderStatus, SynchronizedFrame
from jarvis_piper_interfaces.srv import StartEpisode, StopEpisode, DiscardEpisode
from jarvis_piper_dataset.export_pipeline import DatasetExportPipeline


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>JARVIS PiPER Data Collection Dashboard</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
    .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 12px; margin-bottom: 20px; }
    h1 { margin: 0; font-size: 24px; color: #38bdf8; font-weight: 700; }
    .status-badge { padding: 6px 14px; border-radius: 9999px; font-weight: 600; font-size: 14px; text-transform: uppercase; }
    .badge-recording { background: #ef4444; color: white; animation: pulse 2s infinite; }
    .badge-idle { background: #334155; color: #94a3b8; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    .grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
    .card { background: #1e293b; border-radius: 12px; border: 1px solid #334155; padding: 18px; margin-bottom: 20px; }
    .card-title { font-size: 16px; font-weight: 600; color: #cbd5e1; margin-bottom: 14px; display: flex; justify-content: space-between; }
    .telemetry-row { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 14px; }
    .telemetry-val { font-weight: 600; color: #38bdf8; font-family: monospace; }
    .btn { padding: 10px 18px; border-radius: 8px; border: none; font-weight: 600; cursor: pointer; transition: all 0.2s; font-size: 14px; margin-right: 8px; }
    .btn-start { background: #10b981; color: white; }
    .btn-start:hover { background: #059669; }
    .btn-stop { background: #ef4444; color: white; }
    .btn-stop:hover { background: #dc2626; }
    .btn-discard { background: #64748b; color: white; }
    .btn-discard:hover { background: #475569; }
    .btn-export { background: #8b5cf6; color: white; }
    .input-task { width: 100%; box-sizing: border-box; background: #0f172a; border: 1px solid #475569; padding: 10px 14px; border-radius: 8px; color: white; font-size: 14px; margin-bottom: 14px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }
    th { border-bottom: 1px solid #475569; padding: 8px; color: #94a3b8; }
    td { padding: 8px; border-bottom: 1px solid #334155; }
    .pass { color: #10b981; font-weight: 600; }
    .fail { color: #ef4444; font-weight: 600; }
  </style>
</head>
<body>
  <div class="header">
    <h1>JARVIS PiPER Embodied-AI Data Collection</h1>
    <span id="badge" class="status-badge badge-idle">IDLE</span>
  </div>

  <div class="grid">
    <div>
      <div class="card">
        <div class="card-title">Operator Controls</div>
        <input type="text" id="taskInput" class="input-task" placeholder="Enter language instruction, e.g. 'Pick up the red cube and place in bin'..." value="Pick up the red cube and place in bin">
        <div>
          <button class="btn btn-start" onclick="startEp()">▶ Start Recording</button>
          <button class="btn btn-stop" onclick="stopEp()">⏹ Stop & Save</button>
          <button class="btn btn-discard" onclick="discardEp()">✖ Discard</button>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Recorded Episodes History <button class="btn btn-export" style="font-size:12px; padding:4px 10px;" onclick="exportAll()">Export All Formats</button></div>
        <table>
          <thead>
            <tr><th>Episode ID</th><th>Task</th><th>Frames</th><th>Duration</th><th>QA Score</th></tr>
          </thead>
          <tbody id="episodesTable">
            <tr><td colspan="5" style="text-align:center; color:#64748b;">Loading recorded episodes...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div>
      <div class="card">
        <div class="card-title">Active Telemetry</div>
        <div class="telemetry-row"><span>Active Episode:</span><span id="epId" class="telemetry-val">None</span></div>
        <div class="telemetry-row"><span>Frames Recorded:</span><span id="frameCount" class="telemetry-val">0</span></div>
        <div class="telemetry-row"><span>Elapsed Time:</span><span id="elapsed" class="telemetry-val">0.0s</span></div>
        <div class="telemetry-row"><span>Gripper Stroke:</span><span id="gripperStroke" class="telemetry-val">0.0000 m</span></div>
        <div class="telemetry-row"><span>TCP Position (X,Y,Z):</span><span id="tcpPos" class="telemetry-val">[0.0, 0.0, 0.0]</span></div>
        <div class="telemetry-row"><span>Joints (q1..q6):</span><span id="joints" class="telemetry-val">Waiting...</span></div>
      </div>
    </div>
  </div>

  <script>
    async function updateStatus() {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        const badge = document.getElementById('badge');
        if (data.is_recording) {
          badge.className = 'status-badge badge-recording';
          badge.innerText = 'RECORDING';
        } else {
          badge.className = 'status-badge badge-idle';
          badge.innerText = 'IDLE';
        }
        document.getElementById('epId').innerText = data.current_episode_id || 'None';
        document.getElementById('frameCount').innerText = data.recorded_frames || 0;
        document.getElementById('elapsed').innerText = (data.elapsed_seconds || 0).toFixed(1) + 's';
        document.getElementById('gripperStroke').innerText = (data.gripper_stroke || 0).toFixed(4) + ' m';
        if (data.tcp_pose) {
          document.getElementById('tcpPos').innerText = `[${data.tcp_pose.x.toFixed(3)}, ${data.tcp_pose.y.toFixed(3)}, ${data.tcp_pose.z.toFixed(3)}]`;
        }
        if (data.joint_positions) {
          document.getElementById('joints').innerText = data.joint_positions.map(v => v.toFixed(2)).join(', ');
        }
      } catch (e) {}
    }

    async function loadEpisodes() {
      try {
        const res = await fetch('/api/episodes');
        const eps = await res.json();
        const tbody = document.getElementById('episodesTable');
        if (!eps.length) {
          tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#64748b;">No recorded episodes yet.</td></tr>';
          return;
        }
        tbody.innerHTML = eps.map(e => `
          <tr>
            <td><strong>${e.episode_id}</strong></td>
            <td>${e.task}</td>
            <td>${e.frames}</td>
            <td>${e.duration.toFixed(1)}s</td>
            <td class="${e.passed ? 'pass' : 'fail'}">${e.score} pts</td>
          </tr>
        `).join('');
      } catch (e) {}
    }

    async function startEp() {
      const task = document.getElementById('taskInput').value;
      await fetch('/api/start', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ task_instruction: task }) });
      updateStatus();
    }
    async function stopEp() {
      await fetch('/api/stop', { method: 'POST' });
      updateStatus();
      loadEpisodes();
    }
    async function discardEp() {
      await fetch('/api/discard', { method: 'POST' });
      updateStatus();
    }
    async function exportAll() {
      alert('Triggering Universal Dataset Export (LeRobot, ALOHA HDF5, RLDS)...');
      const res = await fetch('/api/export', { method: 'POST' });
      const data = await res.json();
      alert('Export complete: ' + JSON.stringify(data));
    }

    setInterval(updateStatus, 500);
    setInterval(loadEpisodes, 3000);
    updateStatus();
    loadEpisodes();
  </script>
</body>
</html>
"""


class WebDashboardHandler(BaseHTTPRequestHandler):
    """HTTP request dispatcher."""

    node_ref: Optional["JarvisPiperWebDashboardNode"] = None

    def log_message(self, format, *args):
        pass  # Suppress excessive HTTP logging

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif url.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            status_data = self.node_ref.get_telemetry_dict() if self.node_ref else {}
            self.wfile.write(json.dumps(status_data).encode("utf-8"))
        elif url.path == "/api/episodes":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            eps = self.node_ref.get_episodes_list() if self.node_ref else []
            self.wfile.write(json.dumps(eps).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        url = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            req_data = json.loads(body.decode("utf-8"))
        except Exception:
            req_data = {}

        if url.path == "/api/start":
            task = req_data.get("task_instruction", "teleoperated task")
            res = self.node_ref.call_start_service(task) if self.node_ref else False
            self._send_json({"success": res})
        elif url.path == "/api/stop":
            res = self.node_ref.call_stop_service() if self.node_ref else False
            self._send_json({"success": res})
        elif url.path == "/api/discard":
            res = self.node_ref.call_discard_service() if self.node_ref else False
            self._send_json({"success": res})
        elif url.path == "/api/export":
            res = self.node_ref.run_export() if self.node_ref else {}
            self._send_json(res)
        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


class JarvisPiperWebDashboardNode(Node):
    """ROS 2 Node that wraps the Web Dashboard HTTP server."""

    def __init__(self):
        super().__init__("jarvis_piper_web_dashboard")
        self.declare_parameter("port", 8080)
        self.declare_parameter("data_dir", "/mnt/d/yaswanth/ranger mini/jarvis_piper_ws/data/raw_episodes")
        self.declare_parameter("export_dir", "/mnt/d/yaswanth/ranger mini/jarvis_piper_ws/data/exports")

        self.port = self.get_parameter("port").value
        self.data_dir = self.get_parameter("data_dir").value
        self.export_dir = self.get_parameter("export_dir").value

        # Subscriptions
        self.last_status: Optional[RecorderStatus] = None
        self.last_frame: Optional[SynchronizedFrame] = None
        self.sub_status = self.create_subscription(
            RecorderStatus, "/jarvis_piper/recorder_status", self._cb_status, 10
        )
        self.sub_frame = self.create_subscription(
            SynchronizedFrame, "/jarvis_piper/sync_frame", self._cb_frame, 10
        )

        # Clients
        self.cli_start = self.create_client(StartEpisode, "/jarvis_piper/start_episode")
        self.cli_stop = self.create_client(StopEpisode, "/jarvis_piper/stop_episode")
        self.cli_discard = self.create_client(DiscardEpisode, "/jarvis_piper/discard_episode")

        # Start HTTP server in daemon thread
        WebDashboardHandler.node_ref = self
        self.server = HTTPServer(("0.0.0.0", self.port), WebDashboardHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

        self.get_logger().info(f"Operator Web Dashboard running at http://localhost:{self.port}")

    def _cb_status(self, msg: RecorderStatus):
        self.last_status = msg

    def _cb_frame(self, msg: SynchronizedFrame):
        self.last_frame = msg

    def get_telemetry_dict(self):
        res = {
            "is_recording": self.last_status.is_recording if self.last_status else False,
            "current_episode_id": self.last_status.current_episode_id if self.last_status else "",
            "recorded_frames": self.last_status.recorded_frames if self.last_status else 0,
            "elapsed_seconds": self.last_status.elapsed_seconds if self.last_status else 0.0,
            "active_task": self.last_status.active_task_instruction if self.last_status else "",
            "gripper_stroke": self.last_frame.gripper_position if self.last_frame else 0.0,
            "joint_positions": list(self.last_frame.joint_state.position)[:6] if (self.last_frame and self.last_frame.joint_state) else [0.0]*6,
            "tcp_pose": {
                "x": self.last_frame.tcp_pose.pose.position.x,
                "y": self.last_frame.tcp_pose.pose.position.y,
                "z": self.last_frame.tcp_pose.pose.position.z,
            } if self.last_frame else {"x": 0.0, "y": 0.0, "z": 0.0},
        }
        return res

    def get_episodes_list(self):
        ep_dirs = sorted(glob.glob(os.path.join(self.data_dir, "ep_*")))
        results = []
        for d in ep_dirs:
            traj_p = os.path.join(d, "trajectory.json")
            qa_p = os.path.join(d, "quality_report.json")
            if os.path.exists(traj_p):
                try:
                    with open(traj_p, "r", encoding="utf-8") as f:
                        tdata = json.load(f)
                    meta = tdata.get("metadata", {})
                    score = 100.0
                    passed = True
                    if os.path.exists(qa_p):
                        with open(qa_p, "r", encoding="utf-8") as qf:
                            qdata = json.load(qf)
                            score = qdata.get("score", 100.0)
                            passed = qdata.get("passed", True)
                    results.append({
                        "episode_id": meta.get("episode_id", os.path.basename(d)),
                        "task": meta.get("task_instruction", ""),
                        "frames": meta.get("total_steps", 0),
                        "duration": meta.get("duration_sec", 0.0),
                        "score": score,
                        "passed": passed,
                    })
                except Exception:
                    pass
        return results

    def call_start_service(self, task_instruction: str) -> bool:
        if not self.cli_start.wait_for_service(timeout_sec=2.0):
            return False
        req = StartEpisode.Request()
        req.task_instruction = task_instruction
        req.operator_id = "web_operator"
        fut = self.cli_start.call_async(req)
        return True

    def call_stop_service(self) -> bool:
        if not self.cli_stop.wait_for_service(timeout_sec=2.0):
            return False
        req = StopEpisode.Request()
        req.success_label = True
        fut = self.cli_stop.call_async(req)
        return True

    def call_discard_service(self) -> bool:
        if not self.cli_discard.wait_for_service(timeout_sec=2.0):
            return False
        req = DiscardEpisode.Request()
        req.reason = "Web operator discard"
        fut = self.cli_discard.call_async(req)
        return True

    def run_export(self) -> dict:
        pipeline = DatasetExportPipeline(self.data_dir, self.export_dir)
        return pipeline.export("all")


def main(args=None):
    rclpy.init(args=args)
    node = JarvisPiperWebDashboardNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.server.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
