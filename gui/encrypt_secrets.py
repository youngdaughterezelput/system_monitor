from crypto_utils import SecretManager


def main():
    secret_manager = SecretManager()

    # Введите свои реальные значения
    real_token = input("Введите токен бота: ")
    real_chat_id = input("Введите chat ID: ")

    encrypted_token = secret_manager.encrypt(real_token)
    encrypted_chat_id = secret_manager.encrypt(real_chat_id)

    print("\nЗашифрованные значения (вставьте в код):")
    print(f"'bot_token': '{encrypted_token}'")
    print(f"'chat_id': '{encrypted_chat_id}'")


if __name__ == "__main__":
    main()