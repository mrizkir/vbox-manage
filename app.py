"""
VBox-Manage: Antarmuka web MVC untuk mengelola VM VirtualBox via SOAP (vboxwebsrv).
"""
from flask import Flask
import config
from controllers.vm_controller import vm_bp


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["VBOX_BASE_URL"] = config.get_vbox_base_url()
    app.register_blueprint(vm_bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
