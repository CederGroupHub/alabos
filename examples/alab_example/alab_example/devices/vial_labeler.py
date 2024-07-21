"""Device class for the REINER jetStamp 1025 injket printer used for labeling filled vials."""

import time
from importlib import util
from pathlib import Path
from traceback import print_exc
from typing import ClassVar

import qrcode
from alab_management import BaseDevice, SamplePosition
from alab_management.device_view.device import mock
from alab_management.sample_view.sample import Sample
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont

PRINTER_NAME = "REINER jetStamp 1025"  # ensure this matches device name in Windows printer settings
IMG_HEIGHT = 308
IMG_WIDTH = 1004
FONTSIZE = 21
QR_BOX_SIZE = 7
BLACK_RECT_WIDTH = 25
TOP_BOX_DIM = (500, 44)
LEFT_BOX_DIM = (440, 95)
RIGHT_BOX_DIM = (440, 120)
BOTTOM_BOX_DIM = (500, 44)


@mock(return_constant=Path(__file__).parent.parent / "tasks" / "QR_codes")
def QR_CODE_FOLDER():
    """Return the path to the folder where the QR codes are stored."""
    return Path("D:\\QR_codes")


class VialLabeler(BaseDevice):
    """A device for labeling filled vials."""

    description: ClassVar[str] = (
        "A REINER jetStamp 1025 inket printer for labeling filled vials with QR code and name."
    )

    def __init__(self, *args, **kwargs):
        """Initialize the VialLabeler object."""
        super().__init__(*args, **kwargs)

    def connect(self):
        """Connect to device."""
        self.connected = True

    def disconnect(self):
        """Disconnect from device."""
        self.connected = False

    def emergent_stop(self):
        """Stop device."""
        return

    def is_running(self) -> bool:
        """Check if device is running."""
        return False

    @property
    def sample_positions(self):
        """Return the sample positions of the vial labeler."""
        return [
            SamplePosition(
                "slot",
                description="Slot (location) that can accept one filled vial",
            ),
        ]

    def print_sample_label(self, sample: Sample):
        """Print label onto sample cap. This uses info contained within Sample.metadata (which is either user-specified
        or populated by previously run tasks).

        Args:
            sample: Sample object
                Also looks at sample.metadata and/or sample.tasks for the following properties:
                - target: The target of the sample
                - heating_temperature: The temperature of the sample
                - heating_time: The heating time of the sample
                - powderdosing_results: Identifies the precursors used to create the sample
        """
        try:
            target = sample.metadata.get("target")
            heating_temperature = sample.metadata.get("heating_temperature")
            heating_time = sample.metadata.get("heating_time")
            weight_collected = sample.metadata.get("weight_collected")

            precursors = sample.metadata.get("precursors")
            powderdosing_results = sample.metadata.get("powderdosing_results")
            if powderdosing_results:
                precursors = sorted(
                    [dose["PowderName"] for dose in powderdosing_results["Powders"]]
                )

            date = time.strftime("%m/%d/%y")

            top_text = sample.name
            if len(top_text) >= 20:
                top_text = top_text[:20] + "\n" + top_text[20:]

            left_text = ""
            if heating_temperature is not None:
                left_text += f"{heating_temperature} °C | "
            if heating_time is not None:
                left_text += f"{heating_time} min\n"
            left_text += date
            if weight_collected is not None:
                left_text += f" ({weight_collected} mg)"
            left_text += f"\n {sample.name}"

            right_text = ""
            if precursors:
                if len(precursors) <= 3:
                    right_text = "\n".join(precursors)
                elif len(precursors) == 4:
                    right_text = (
                        ", ".join(precursors[:2]) + ",\n" + ", ".join(precursors[2:4])
                    )
                else:  #  This should look okay for up to 6 precursors (more will be cut off; this is okay)
                    right_text = (
                        ", ".join(precursors[:2])
                        + ",\n"
                        + ", ".join(precursors[2:4])
                        + ",\n"
                        + ", ".join(precursors[4:])
                    )

            elif sample.tags:  # only space to print tags if no precursors
                right_text = "\n".join(sample.tags)

            bottom_text = target or str(sample.sample_id)

            img = Image.new(
                mode="RGBA", size=(IMG_WIDTH, IMG_HEIGHT), color=(0, 0, 0, 1)
            )

            top_fontsize = FONTSIZE + 12 if len(top_text) < 16 else FONTSIZE + 7

            top_label = get_text_img(
                top_text,
                TOP_BOX_DIM,
                (TOP_BOX_DIM[0] / 2, TOP_BOX_DIM[1] / 2),
                top_fontsize,
                bold=True,
            )
            left_label = get_text_img(
                left_text,
                LEFT_BOX_DIM,
                (LEFT_BOX_DIM[0] / 2, LEFT_BOX_DIM[1] / 2),
                FONTSIZE,
            )
            if precursors:
                right_label = get_text_img(
                    right_text,
                    RIGHT_BOX_DIM,
                    (RIGHT_BOX_DIM[0] / 2, RIGHT_BOX_DIM[1] / 2),
                    (
                        FONTSIZE
                        if all(len(p) < 20 for p in right_text.split("\n"))
                        else FONTSIZE - 5
                    ),
                )
            else:
                right_label = get_text_img(
                    right_text,
                    RIGHT_BOX_DIM,
                    (RIGHT_BOX_DIM[0] / 2, RIGHT_BOX_DIM[1] / 2),
                    FONTSIZE - 2,
                )
            if len(bottom_text) < 10:
                bottom_fontsize = FONTSIZE + 12
            elif len(bottom_text) < 20:
                bottom_fontsize = FONTSIZE + 7
            elif len(bottom_text) < 30:
                bottom_fontsize = FONTSIZE + 2
            else:
                bottom_fontsize = FONTSIZE - 6

            bottom_label = get_text_img(
                bottom_text,
                BOTTOM_BOX_DIM,
                (BOTTOM_BOX_DIM[0] / 2, BOTTOM_BOX_DIM[1] / 2 - 5),
                bottom_fontsize,
                bold=True,
            )

            qr_img = get_qr_img(sample.sample_id)

            # draw some black rectangles to prime the printer
            draw_rect = ImageDraw.Draw(img)
            draw_rect.rectangle((0, 0, BLACK_RECT_WIDTH, IMG_HEIGHT), fill="black")
            draw_rect.rectangle(
                (
                    BLACK_RECT_WIDTH * 2,
                    0,
                    BLACK_RECT_WIDTH * 2 + BLACK_RECT_WIDTH,
                    IMG_HEIGHT,
                ),
                fill="black",
            )
            draw_rect.rectangle(
                (
                    BLACK_RECT_WIDTH * 4,
                    0,
                    BLACK_RECT_WIDTH * 4 + BLACK_RECT_WIDTH,
                    IMG_HEIGHT,
                ),
                fill="black",
            )
            draw_rect.rectangle(
                (
                    BLACK_RECT_WIDTH * 6,
                    0,
                    BLACK_RECT_WIDTH * 6 + BLACK_RECT_WIDTH,
                    IMG_HEIGHT,
                ),
                fill="black",
            )

            center = IMG_WIDTH / 1.7

            img.paste(
                left_label.rotate(90, expand=True),
                ((int(center - left_label.height - qr_img.width / 2), -50)),
            )
            img.paste(
                right_label.rotate(270, expand=True),
                ((int(center + qr_img.width / 2) - 10, -45)),
            )
            img.paste(top_label, ((int(center - top_label.width / 2), 13)))
            img.paste(
                bottom_label,
                (
                    (
                        int(center - bottom_label.width / 2),
                        int(IMG_HEIGHT - bottom_label.height / 2 - 15),
                    )
                ),
            )

            img.paste(qr_img, (int(center - qr_img.width / 2), int(0.22 * IMG_HEIGHT)))

            filepath = QR_CODE_FOLDER() / f"{sample.sample_id}.pdf"
            img.save(filepath)
            time.sleep(5)
            print_file(filepath.as_posix())
            return img
        except Exception as e:
            print_exc()
            raise e


def get_qr_img(sample_id: str):
    """Returns a PIL image of a QR code with the given sample string."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=QR_BOX_SIZE,
        border=0,
    )
    qr.add_data(sample_id)
    qr.make(fit=True)

    return qr.make_image(fill_color="black", back_color="transparent").get_image()


def get_text_img(text, box_dim, coords, fontsize, bold=False):
    """Get a PIL Image object of a box with centered text."""
    img = Image.new("RGBA", box_dim)

    font_name = font_manager.FontProperties(
        family="sans-serif", weight="bold" if bold else "normal"
    )
    font_file = font_manager.findfont(font_name)
    font = ImageFont.truetype(font_file, fontsize)
    draw = ImageDraw.Draw(img)
    draw.text(
        xy=coords, text=text, font=font, fill="black", align="center", anchor="mm"
    )
    return img


@mock(return_constant=None)
def print_file(filename):
    """Call Windows API to print a file."""
    try:
        import win32api
    except ImportError:
        raise ImportError(
            f"win32api is not installed! Printing with {PRINTER_NAME} is only available on Windows."
        )

    # try:
    for _ in range(2):  # print twice to ensure label is printed
        win32api.ShellExecute(0, "print", filename, f'"{PRINTER_NAME}"', ".", 0)
        time.sleep(5)  # TODO: find a better way to wait for print job to finish
    print(f"Printed label from {filename}.")
    # except Exception as e:
    #     print_exc()
    #     raise OSError(f"Failed to print label from {filename}.") from e
