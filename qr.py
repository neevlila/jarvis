import qrcode
try:
    import tkinter as tk
    from tkinter import ttk
except Exception:
    tk = None
    ttk = None
try:
    from PIL import Image, ImageTk
    _PIL_AVAILABLE = True
except Exception:
    Image = None
    ImageTk = None
    _PIL_AVAILABLE = False
import tempfile
import time
import os

def main():
    root = tk.Tk()
    root.title("JARVIS — Generate QR")
    root.geometry("520x220")
    root.configure(bg="#101418")

    style = ttk.Style()
    style.theme_use('clam')
    style.configure('TLabel', foreground='#E6EDF3', background='#101418')
    style.configure('TEntry', fieldbackground='#1C2329', foreground='#E6EDF3')
    style.configure('TButton', padding=6, relief='flat', background='#2D3742', foreground='#E6EDF3')

    header = ttk.Label(root, text="Generate a QR Code", font=('Segoe UI', 16, 'bold'))
    header.pack(pady=(14, 6))

    desc = ttk.Label(root, text="Enter any text or URL and click Generate")
    desc.pack(pady=(2, 8))

    entry = ttk.Entry(root, width=56)
    entry.pack(pady=4)

    status = ttk.Label(root, text="")
    status.pack(pady=6)

    viewer = None
    temp_path = None
    final_saved = False

    def show_qr(img):
        nonlocal viewer, temp_path, final_saved
        final_saved = False
        fd, temp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        img.save(temp_path)
        if viewer is None or not tk.Toplevel.winfo_exists(viewer):
            viewer = tk.Toplevel(root)
            viewer.title("QR Preview")
            viewer.configure(bg="#101418")
        else:
            for w in viewer.winfo_children():
                w.destroy()
        if _PIL_AVAILABLE:
            try:
                pil_img = Image.open(temp_path)
                short = min(480, max(pil_img.size))
                pil_img = pil_img.resize((short, short))
                pic = ImageTk.PhotoImage(pil_img)
                lbl = ttk.Label(viewer)
                lbl.configure(image=pic)
                lbl.image = pic
                lbl.pack(padx=12, pady=12)
            except Exception:
                ttk.Label(viewer, text="QR generated (preview not available)").pack(padx=12, pady=12)
        else:
            try:
                pic = tk.PhotoImage(file=temp_path)
                lbl = ttk.Label(viewer)
                lbl.configure(image=pic)
                lbl.image = pic
                lbl.pack(padx=12, pady=12)
            except Exception:
                ttk.Label(viewer, text="QR generated (preview not available)").pack(padx=12, pady=12)

        def on_close_viewer():
            nonlocal final_saved
            if not final_saved:
                ts = time.strftime("%Y%m%d_%H%M%S")
                fname = f"qr_{ts}.png"
                try:
                    os.replace(temp_path, fname)
                except Exception:
                    try:
                        import shutil
                        shutil.copyfile(temp_path, fname)
                    except Exception:
                        pass
                final_saved = True
            viewer.destroy()
            status.config(text=f"Saved {os.path.abspath(fname)}")

        viewer.protocol("WM_DELETE_WINDOW", on_close_viewer)

    def on_generate():
        text = entry.get().strip()
        if not text:
            status.config(text="Please enter text")
            return
        try:
            img = qrcode.make(text)
            show_qr(img)
            status.config(text="QR generated. Close preview to save.")
        except Exception as e:
            status.config(text=f"Error: {e}")

    ttk.Button(root, text="Generate", command=on_generate).pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()