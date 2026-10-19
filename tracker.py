"""Manual local tracker. Production scheduling calls the deployed web app."""
if __name__ == "__main__":
    import app
    from services.shop_tracker import check_shop
    print(check_shop(app, send_email=True))
