from tkinter import Tk, Label, Button

# Ask user for key and URL
# Validate above by connection attempt
# Create install directory
# Extract winsw.exe
# Extract worker.exe
# Extract uninstaller (or copy this file if it's the installer)
# Create winsw config (templated key)
# Register uninstaller
# Install + start service via winsw
# Check service is running

class Installer:
    def __init__(self, master):
        self.master = master
        master.title("dsportal worker installer")

        self.label = Label(master, text="Welcome to the dsportal worker windows service installer.")
        self.label.pack(pady=20,padx=10)

        self.greet_button = Button(master, text="Greet", command=self.greet)
        self.greet_button.pack(pady=20,padx=10)

        self.close_button = Button(master, text="Close", command=master.quit)
        self.close_button.pack(pady=20,padx=10)

    def greet(self):
        print("Greetings!")

root = Tk()
my_gui = Installer(root)
root.mainloop()