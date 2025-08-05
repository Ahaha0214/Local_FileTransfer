import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import socket
import threading
import os

# --- 常數設定 ---
PORT = 17888
BUFFER_SIZE = 4096 # 每次讀取/傳送的緩衝區大小
SEPARATOR = "<SEPARATOR>" # 檔案名稱和大小之間的分隔符號

class FileTransferApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("檔案傳輸工具 (簡易版)")
        self.geometry("480x350") # 調整為較小的視窗

        # 樣式設定
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton", padding=6, relief="flat", font=('Helvetica', 10))
        style.configure("TLabel", font=('Helvetica', 11))
        style.configure("Header.TLabel", font=('Helvetica', 14, 'bold'))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=10, padx=10, expand=True, fill="both")

        # --- 建立頁籤 ---
        self.server_frame = ttk.Frame(self.notebook, padding="10")
        self.client_frame = ttk.Frame(self.notebook, padding="10")
        
        self.notebook.add(self.server_frame, text='接收檔案 (Server)')
        self.notebook.add(self.client_frame, text='傳送檔案 (Client)')

        # 初始化變數
        self.selected_filepath = ""

        # --- 建立介面元件 ---
        self.create_server_widgets()
        self.create_client_widgets()
        
        # 當視窗關閉時，確保程式完全退出
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        # 簡單地關閉所有可能正在運行的socket和線程
        os._exit(0)

    def get_local_ip(self):
        """取得本機IP位址的可靠方法"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # 不需要實際連線，只是為了觸發系統取得對應的網路介面
            s.connect(('8.8.8.8', 1))
            ip = s.getsockname()[0]
        except Exception:
            # 如果無法連線到外部，則回傳本地主機
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    # =================================================================
    # 接收方 (Server) 的介面與邏輯
    # =================================================================
    def create_server_widgets(self):
        ttk.Label(self.server_frame, text="注意，連線需先在同個區網", style="Header.TLabel").pack(pady=(0, 10))
        ttk.Label(self.server_frame, text="第一步：啟動接收服務", style="Header.TLabel").pack(pady=(0, 10))
        
        local_ip = self.get_local_ip()
        ttk.Label(self.server_frame, text=f"請將此IP位址告訴傳送方:").pack(pady=5)
        ip_entry = ttk.Entry(self.server_frame, font=('Helvetica', 12, 'bold'), justify='center')
        ip_entry.insert(0, local_ip)
        ip_entry.config(state='readonly')
        ip_entry.pack(pady=5, padx=10, fill="x")

        self.server_button = ttk.Button(self.server_frame, text="啟動接收服務", command=self.start_server_thread)
        self.server_button.pack(pady=20, fill="x")

        ttk.Label(self.server_frame, text="狀態日誌:", anchor="w").pack(pady=(10, 0), fill="x")
        self.server_status_label = ttk.Label(self.server_frame, text="尚未啟動", wraplength=450, relief="sunken", padding=5)
        self.server_status_label.pack(expand=True, fill="both")

    def start_server_thread(self):
        # 使用線程來運行伺服器邏輯，避免GUI卡死
        self.server_button.config(state="disabled")
        server_thread = threading.Thread(target=self.server_logic)
        server_thread.daemon = True # 確保主程式退出時線程也退出
        server_thread.start()

    def update_server_status(self, message):
        self.server_status_label.config(text=message)

    def server_logic(self):
        self.update_server_status(f"服務已啟動，正在埠號 {PORT} 等待連線...")
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(('0.0.0.0', PORT))
            s.listen(1)
            
            client_socket, address = s.accept()
            self.update_server_status(f"接受來自 {address} 的連線。")
            
            # 接收檔案資訊
            received = client_socket.recv(BUFFER_SIZE).decode()
            filename, filesize = received.split(SEPARATOR)
            filename = os.path.basename(filename) # 清理路徑，只取檔名
            filesize = int(filesize)
            
            self.update_server_status(f"準備接收檔案: {filename}\n檔案大小: {filesize} bytes")
            
            # 準備接收檔案
            with open(filename, "wb") as f:
                bytes_received = 0
                while bytes_received < filesize:
                    bytes_to_read = min(BUFFER_SIZE, filesize - bytes_received)
                    data = client_socket.recv(bytes_to_read)
                    if not data:
                        break # 連線中斷
                    f.write(data)
                    bytes_received += len(data)
                    progress = (bytes_received / filesize) * 100
                    self.update_server_status(f"正在接收 {filename}... {progress:.2f}%")

            self.update_server_status(f"檔案 {filename} 接收成功！")
            messagebox.showinfo("成功", f"檔案 '{filename}' 已成功儲存。")

        except Exception as e:
            self.update_server_status(f"錯誤: {e}")
            messagebox.showerror("錯誤", f"發生錯誤: {e}")
        finally:
            if 's' in locals():
                s.close()
            self.server_button.config(state="normal") # 讓按鈕可以再次點擊

    # =================================================================
    # 傳送方 (Client) 的介面與邏輯
    # =================================================================
    def create_client_widgets(self):
        ttk.Label(self.client_frame, text="第二步：傳送檔案給對方", style="Header.TLabel").pack(pady=(0, 10))

        ttk.Label(self.client_frame, text="請輸入接收方的IP位址:").pack()
        self.ip_entry = ttk.Entry(self.client_frame, font=('Helvetica', 12))
        self.ip_entry.pack(pady=5, padx=10, fill="x")

        ttk.Button(self.client_frame, text="選擇要傳送的檔案", command=self.select_file).pack(pady=10, fill="x")
        self.selected_file_label = ttk.Label(self.client_frame, text="尚未選擇檔案", wraplength=450)
        self.selected_file_label.pack(pady=5)

        self.send_button = ttk.Button(self.client_frame, text="傳送檔案", command=self.start_client_thread, state="disabled")
        self.send_button.pack(pady=10, fill="x")

        ttk.Label(self.client_frame, text="狀態日誌:", anchor="w").pack(pady=(10, 0), fill="x")
        self.client_status_label = ttk.Label(self.client_frame, text="請先設定IP並選擇檔案", wraplength=450, relief="sunken", padding=5)
        self.client_status_label.pack(expand=True, fill="both")

    def select_file(self):
        self.selected_filepath = filedialog.askopenfilename()
        if self.selected_filepath:
            filename = os.path.basename(self.selected_filepath)
            self.selected_file_label.config(text=f"已選擇: {filename}")
            self.send_button.config(state="normal") # 檔案選擇後，啟用傳送按鈕
        else:
            self.selected_file_label.config(text="尚未選擇檔案")
            self.send_button.config(state="disabled")

    def start_client_thread(self):
        target_ip = self.ip_entry.get()
        if not target_ip:
            messagebox.showwarning("警告", "請輸入接收方的IP位址。")
            return
        if not self.selected_filepath:
            messagebox.showwarning("警告", "請選擇要傳送的檔案。")
            return

        self.send_button.config(state="disabled")
        client_thread = threading.Thread(target=self.client_logic, args=(target_ip,))
        client_thread.daemon = True
        client_thread.start()
        
    def update_client_status(self, message):
        self.client_status_label.config(text=message)

    def client_logic(self, target_ip):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            filesize = os.path.getsize(self.selected_filepath)
            filename = os.path.basename(self.selected_filepath)

            self.update_client_status(f"準備連線至 {target_ip}:{PORT}...")
            s.connect((target_ip, PORT))
            self.update_client_status("連線成功！正在傳送檔案資訊...")

            # 傳送檔案名稱和大小
            s.send(f"{filename}{SEPARATOR}{filesize}".encode())

            # 傳送檔案內容
            bytes_sent = 0
            with open(self.selected_filepath, "rb") as f:
                while bytes_sent < filesize:
                    data = f.read(BUFFER_SIZE)
                    if not data:
                        break # 讀取完畢
                    s.sendall(data)
                    bytes_sent += len(data)
                    progress = (bytes_sent / filesize) * 100
                    self.update_client_status(f"正在傳送 {filename}... {progress:.2f}%")
            
            self.update_client_status("檔案傳送成功！")
            messagebox.showinfo("成功", f"檔案 '{filename}' 已成功傳送。")

        except FileNotFoundError:
            self.update_client_status("錯誤：找不到指定的檔案。")
            messagebox.showerror("錯誤", "找不到指定的檔案，請重新選擇。")
        except ConnectionRefusedError:
            self.update_client_status("錯誤：連線被拒絕。請確認接收方已啟動服務且IP位址正確。")
            messagebox.showerror("錯誤", "連線被拒絕。\n請確認接收方已啟動服務且IP位址正確。")
        except socket.gaierror:
             self.update_client_status(f"錯誤：無效的IP位址 '{target_ip}'。")
             messagebox.showerror("錯誤", f"無效的IP位址 '{target_ip}'。")
        except Exception as e:
            self.update_client_status(f"發生未知錯誤: {e}")
            messagebox.showerror("錯誤", f"發生未知錯誤: {e}")
        finally:
            if 's' in locals():
                s.close()
            self.send_button.config(state="normal")

if __name__ == "__main__":
    app = FileTransferApp()
    app.mainloop()
