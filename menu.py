import meraki_dns


# Afficher le menu
def show_menu():
    print("*" * 12)
    print("MENU")
    print("*" * 12)
    print("1. list networks")
    print("2. list profiles")
    print("3. show records")
    print("4. show config")
    print("5. apply config")

    choix = input("Choose an option: ")
    while choix not in ["1", "2", "3", "4", "5"]:
        choix = input("Invalid option. Choose again: ")
    match choix:
        case "1":
            meraki_dns.list_networks()
            loop_menu()
        case "2":
            meraki_dns.list_profiles()
            loop_menu()
        case "3":
            meraki_dns.list_records()
            loop_menu()
        case "4":
            meraki_dns.read_config("config.yml")
            loop_menu()
        case "5":
            meraki_dns.apply_config("config.yml")
            loop_menu()
        case _:
            print("Invalid option")
            loop_menu()


def loop_menu():
    choix = (input("Back to main menu (y/n) ? "))
    match choix:
        case "y":
            show_menu()
        case "n":
            exit()
        case _:
            print("Choix invalide.")
            show_menu()


if __name__ == '__main__':
    show_menu()
