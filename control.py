import subprocess
import sys

print("╔══════════════════════════════════╗")
print("║ AI Room Brightness Controller    ║")
print("║                                  ║")
print("║  1 → Manual Mode (voice)         ║")
print("║  2 → Automatic Mode (camera)     ║")
print("║  q → Quit                        ║")
print("╚══════════════════════════════════╝\n")

while True:
    choice = input("Select mode (1/2/q): ").strip()

    if choice == "1":
        print("\nStarting Manual Mode...\n")
        subprocess.run([sys.executable, "manual.py"])
        break
    elif choice == "2":
        print("\nStarting Automatic Mode...\n")
        subprocess.run([sys.executable, "automatic.py"])
        break
    elif choice.lower() == "q":
        print("Bye!")
        break
    else:
        print("  Invalid choice — enter 1, 2 or q")
