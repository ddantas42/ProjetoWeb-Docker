import socket
import threading
import json
import logging

logger = logging.getLogger(__name__)

def handle_client(conn, addr, process_func):
    logger.info(f"Socket client connected from {addr}")
    with conn:
        buffer = ""
        while True:
            try:
                data = conn.recv(4096)
                if not data:
                    break
                buffer += data.decode('utf-8')
                
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if not line.strip():
                        continue
                    
                    try:
                        req = json.loads(line)
                        response = process_func(req)
                        conn.sendall((json.dumps(response) + '\n').encode('utf-8'))
                    except json.JSONDecodeError:
                        err = {'success': False, 'error': 'Invalid JSON'}
                        conn.sendall((json.dumps(err) + '\n').encode('utf-8'))
            except Exception as e:
                logger.error(f"Socket error with {addr}: {e}")
                break
    logger.info(f"Socket client disconnected: {addr}")

def start_socket_server(process_func, host='0.0.0.0', port=9000):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)
    logger.info(f"Socket server listening on {host}:{port}")
    
    while True:
        try:
            conn, addr = server.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr, process_func))
            client_thread.daemon = True
            client_thread.start()
        except Exception as e:
            logger.error(f"Socket server accept error: {e}")
