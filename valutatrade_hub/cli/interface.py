import prompt

from valutatrade_hub.core.usecases import register

def run():
	while True:
		full_command = input()
		command = full_command.split()[0]

		match command:
			case "register":
				register()
			case "exit":
				break