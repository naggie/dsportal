from tkinter import Tk, Label, Button

class Installer:
    def __init__(self, master):
        self.master = master
        master.title("dsportal worker installer")

        self.label = Label(master, text="Welcome to the dsportal worker windows service installer.")
        self.label.pack()

        self.greet_button = Button(master, text="Greet", command=self.greet)
        self.greet_button.pack()

        self.close_button = Button(master, text="Close", command=master.quit)
        self.close_button.pack()

    def greet(self):
        print("Greetings!")

root = Tk()
my_gui = Installer(root)
root.mainloop()
