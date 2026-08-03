import http.server
import json

class WebhookHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        print("\n" + "="*50)
        print("🚀 WEBHOOK RECEIVED!")
        print("="*50)
        
        print("\n--- Headers ---")
        for k, v in self.headers.items():
            if k.lower().startswith('x-ghost'):
                print(f"✅ {k}: {v}")
            else:
                print(f"  {k}: {v}")
                
        print("\n--- Payload ---")
        try:
            parsed = json.loads(post_data.decode('utf-8'))
            print(json.dumps(parsed, indent=4))
        except:
            print(post_data.decode('utf-8'))
            
        print("="*50 + "\n")
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status": "success"}')
        
    def log_message(self, format, *args):
        # Suppress default logging to keep terminal clean
        pass

if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', 9001), WebhookHandler)
    print("\n🎧 Local Webhook Listener Started!")
    print("👉 Set your Ghost Webhook URL to: http://localhost:9001")
    print("Waiting for conversions...\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping listener...")
