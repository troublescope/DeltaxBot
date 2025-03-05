from app.helpers import ButtonMaker


class Keyboard:
    @staticmethod
    def back():
        return ButtonMaker().add_button("« Beranda", callback_data="home").build()

    @staticmethod
    def cancel():
        return ButtonMaker().add_button("Batalkan", callback_data="cancel").build()

    @staticmethod
    def close():
        return ButtonMaker().add_button("Tutup", callback_data="close").build()

    @staticmethod
    def home():
        return (
            ButtonMaker()
            .add_button("Seting Panel", callback_data="seting_panel_menu")
            .add_button("Sambutan", callback_data="seting_panel_start")
            .add_row()
            .add_button("❌ Tutup", callback_data="close")
            .build()
        )

    @staticmethod
    def setting_panel_main():
        return (
            ButtonMaker()
            .add_button("VIP", callback_data="seting_panel_vip")
            .add_button("Promo", callback_data="seting_panel_promo")
            .add_row()
            .add_button("« Kembali", callback_data="home")
            .build()
        )

    @staticmethod
    def seting_panel_vip():
        return (
            ButtonMaker()
            .add_button("Tambah", callback_data="seting_panel_vip_add")
            .add_button("Preview", callback_data="seting_panel_vip_preview")
            .add_button("Hapus", callback_data="seting_panel_vip_del")
            .add_row()
            .add_button("« Kembali", callback_data="seting_panel_menu")
            .build()
        )

    @staticmethod
    def seting_panel_promo():
        return (
            ButtonMaker()
            .add_button("Tambah", callback_data="seting_panel_promo_add")
            .add_button("Hapus", callback_data="seting_panel_promo_del")
            .add_row()
            .add_button("« Kembali", callback_data="seting_panel_menu")
            .build()
        )

    @staticmethod
    def sambutan_menu():
        return (
            ButtonMaker()
            .add_button("VIP Sambutan", callback_data="seting_panel_start_vip")
            .add_button("Promo Sambutan", callback_data="seting_panel_start_promo")
            .add_row()
            .add_button("Start menu", callback_data="set_welcome_start")
            .add_row()
            .add_button("« Kembali", callback_data="home")
            .build()
        )

    @staticmethod
    def start():
        return (
            ButtonMaker()
            .add_button("Pesan", callback_data="start_text")
            .add_button("Photo", callback_data="start_photo")
            .add_row()
            .add_button("« Kembali", callback_data="home")
            .build()
        )
