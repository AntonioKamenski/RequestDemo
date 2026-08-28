import json
from http.server import BaseHTTPRequestHandler, HTTPServer

songQueueRef = None

def song_queue_to_list():
  global songQueueRef
  return [f"{song.songName} - {song.artist}" for song in songQueueRef]

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
      return
    def do_GET(self):

        if self.path == "/data":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(song_queue_to_list()).encode())
            return

        # Main page
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"""
<!DOCTYPE html>
<html>

<ul id="list"></ul>

<script>
async function update() {
  try {
    const res = await fetch('/data');
    const data = await res.json();

    const list = document.getElementById('list');
    list.innerHTML = '';

    data.forEach(item => {
      const li = document.createElement('li');
      li.textContent = item;
      list.appendChild(li);
    });

  } catch (e) {
    console.error(e);
  }
}

setInterval(update, 1000);
update();
</script>
</body>
</html>
""")

import threading

def run(songQueue=[], port=3000):
    global songQueueRef
    songQueueRef = songQueue

    def start_server():
        server = HTTPServer(("127.0.0.1", port), Handler)
        print(f"Server running at http://127.0.0.1:{port}")
        server.serve_forever()

    thread = threading.Thread(target=start_server, daemon=True)
    thread.start()

if __name__ == "__main__":
    run()