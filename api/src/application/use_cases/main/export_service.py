from uuid import UUID
from application.ports.input.i_export_service import IExportService
from application.ports.output.i_release_repository import IReleaseRepository
from application.ports.output.i_verification_result_repository import IVerificationResultRepository
from application.ports.output.i_project_repository import IProjectRepository
from core.logger import get_logger
import asyncio
import tempfile
import csv
import os
from datetime import datetime, timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image,
)
from reportlab.lib import colors
from reportlab.platypus.flowables import Flowable

_log = get_logger(__name__)

_LOGO_B64_UNUSED = (  # reserved — not used at runtime
    "iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAYAAABS3GwHAAAQAElEQVR4Aex9B2BcxbX2N/duU5cs"
    "yb1I7t3YBhuwDQZTA4QWSgIvhSTk5700SpL3QgrJew/yEhJaGqTRIQkJPYDBxt0Y27j3Jrmq2erS"
    "anfvnf+c2aLd1VZpJa1syXfunTtz5sw5Z86Ze+bM3WsN/X8pk0BxycLBOWMuOD+3dMHteaPm30/X"
    "X+aMWvCH3JIFL+eWzP9Xzqj5K3NK5m/JLVlwKGfUgpqcUfOlNy2oyR214CDX0f3KXILNpTY5oxY8"
    "xTh8uG5n3ANLFw1KGcH9iNBvAEkqQcHoS/JyS+ZfkTtq/r+TYj5MSvtPSpuprMEpPSfgMVdLUz5n"
    "Av9D13sA+RUp5S1S4krqaj4kptN9CZUX0r3vkIUSspTrqGA+wxLMLQTzVcbhw/Uc42412yq4r5yS"
    "+Zsp/TNv1IJf5JUsuCu3ZMHluZMvH0Dt+48kJNBvAHGExQqfX7LgutyS+Y+Swm32GM5aUtB3JPAB"
    "Usx7SWmvpzSDynLioEpZtepLYgYkrjch7zOl/C0ZzLuyubma6NyUW7LgEaL52n6DiC/yfgMIk1Ek"
    "hTekfJWU7lukcDMIXFBK10MjOs+SUn6baH6t3yDiD1O/AZCMBk2/LCu39ILP55bMX0wz/ClSnr6i"
    "8ER9zCPcICpzRy14K7dkwa3Mc8yWZ0jlGWsADzzwgEaKcDkpxHOt9a2V0jSfodnzUhr301kmFlpr"
    "XEVPiJeYZ+Y9r/SCyx544IHTmWca0ujHGcd4fsnCs/JGzX/4l3/54CgpwrukELdTyoouotOzhnmm"
    "dLtpmu+RLI6wTPJLL2IX7/RkOApXZ4QBDBhzwQga4PtpEbvLkJ5NavEKDIkikzOxeCjLxDDdHFna"
    "lTdqwfdZZmeCIE5rA2A/l9ycb7s9cg0N8P/QInbimTCoXeJRYqIJ+b8ss9ySC77FMuwSvjRvfFoa"
    "AIfvckvmP9BS31pObs4jFE8fnubjkIbkyeFSmo+yDEmWP2aZpiGRXSbptDKAAWMXDs+lGDiaWw7T"
    "gvbHgCzssmsagQHtMXRvr0lhp006iQdYpiTbX7GMcRr9nRYGMHbslXaKaPzU7TH2S4qB0+KuTy9q"
    "03GjgWVKsr2bZUyG8BOW+elgB33eAHJGz7+6yt24gwboh5DS3ucHJb2m/47iJBmTIfyIZZ436oKL"
    "OwL0rRKtb5HbTi1HKXJHzX8TBt4knRnTXhOao7rQgi7d9cDc3ANddEkEvsYk1zEmzCX0NHiZx8J"
    "X3Ocufc4AFi5caMkrueA/PR5zNw3C1fEknlp9oh7jdXiG1dPT4BYei7yS+d/jselr7PcpA8ijR+"
    "7GQ54tpjQfIlXM7GvCPl3p5bEwJX7GY8NjlM58htPWJwyA37PPLZn/V37kEgOTKXX/QaPa/Z2c"
    "dj1M5jHKLVnwMo9ZX+Au7Q1gwNiLprRJzyoKa97cowJNre/UA6SnD8HsFjml5wMeu x5gvEtdpLUB"
    "kF95p9vtXk+TcdRFbpe4P60ak5TSi58pPHZ5pQu+ml5khVKTlgZQPHlhdk7JglfJr3ySyM2g1H/0"
    "mAToSZI6W8owTfkUjyWPaY+xkERHaWcAeWPmz25r9mymmP51SfDRD5oyCZD2kw2kDB0jkvI6HlMe"
    "W75Np5Q2BkB+o8gZNf8e08BaGoJucHl6T+zET+913ps9BzFOa7gxPLa0QL67N0kK7zstDIC31XNL"
    "F/yRiPslpLDS9bQ6Uj2h9hnhhDMuYaWJ7lc5JfP/dNNNN+npwEevGwD/BrfS0/geJO7wCiRo2vAW"
    "9J9PBwkEjIEyNNbvrT/xJo99b7PWqwYwYOzC4R7DuZqU/8LeFkR//z0lAe8ERy7RlTz2rAM91XOk"
    "fnrNAAZQfN/tNtYSUVMonVGH1AS8SaMrJ+/9GSUEL7MUKjXWsi54b3v+3CsGkF+y4EKPx7MakKft"
    "D1UkP+ntFshMe1iyATYLYKVk0QBOnKcymWkLg6W2jINwxVIN75waA6I7qhLpNBEY0gHWBdaJ7iAz"
    "Hk4tHkCq6/NK599kAO/RYigv1bhTjS+R8WMYKbwzuGQlziKlpQQHKbrHhGhpC0suCKcboo2SywPB"
    "ifNc1kJ1YfAgHIxLEk6VuA9+gnCfPobj2IcPKsWXRDpNBIYEyLrAOsG6kWIq46LrUQPILZn/WdPE"
    "yxTj7xPv7ccaP+XCkDKCZmhYdcBCyTAgmknhObWSMhtm3AGIByAIh2BcjJMSqA/VF/dJ/Suj07V4"
    "aHz1sTjygfT0xU+SlHbWDYoG3t6TJCQquS7TlF8yfyEtfJ4lRD3WJ/XV+YNmpvDGXCRJ8XgmVkrv"
    "MQCX4Z3FeSY3GCK8VWrvBfWhnhrUH9wGwDSQG8U0SZtO8YRY/YXRF3Ybq2UP1WnSlH/pyTdKe0QZ"
    "c0dfeA7NhW+QEMnxpXNfOHwzE+uIpLzkGT6bHlyUB83Eoo3cF1NCkFX3Fjvct2AaiBamSdGR7QDT"
    "qmhWBTFOzEukahmpsMfKLFKYr9GTYE5P9NjtBpA3bv5oaZjvkJ702MdjUyU4dnOUi0OuBuMUTS80"
    "2xuIpjcM01uJaRL8NGpyeklgmsk9kwm7R95m6szIVKbnT2x7rCvSxL/yxl7c5TcC4nHQrQZQNOHS"
    "odKF9ynaUxiPkHSq50EwHVZIjs6wm0EzrGBXI4VEsnG5Z46Ge+54CoWmVuMUrUQzu0j8NFC8pJD2"
    "7kTVLglZKN2u91iHurO/bjOAnImLCtucrYtJmUZ3JwOpxE20Quo0BFkOCIq+aBydYRcjRZ0o/HYr"
    "jFHFcH7rGrhumQ/X9efCeepen4Rk7GJKNLkV9ERdg90jxQLyAeGLemIaOXTB0x9LeLiFax5AOkRF"
    "8utu8h24xgJKShQ7hdL0DoM9scvGMDFJOjrCIZicZgEHkp+7gaI3nvAlwfuVSuK6dC8vH+5D5k5e"
    "R+aMXYVmzG+7LZ8J552XwzJsEmUEh1JCuu6ag/ERgnqBTpIp4VLyG4CdVC7lPq5upbc7a10pIp9A"
    "Nf91iACfheZRiu+d0A73dgpIjO6DZFxxZYdchhb2wsrnPKkXLf94Iz/kTYV2+HfY/fwDL6l1Q4U3q"
    "07J2DxxPL4X1vc3wzBlLsDeEuUYyNRRRX4pHXhtQSg3SnsAiL2ad6o6eUm4A+aPm8/+Y8rXuIDTV"
    "ONmt2O0AbSoJ3oSi1VdX5lqFjxCw0psUjfGMG4LWe66F67MXwLZkKxyPvAHL9sPQaKFKYAF2OC8o"
    "smTZcwyOx96C7c0NcF03B633XQfP5BEwczLAOBOK7ASwdsyofpjHVjcty+ggo2ecHSHTsETia3mj"
    "F9yYashSagDFJQsHmxB/TjWRncMXu5WKjpACgBa3wuUJA2ZVCSuKccu4JMXiQREXmWEHuzFtX7wY"
    "7itnw0qze+YDL8HKMz6tJ4LRSHZHmIagQvbbrRv2I/PHL8O6cifcF01F2x2L4FkwGTI7A6oP7odS"
    "ULOks4pn4p3dPqY/aQS90EAa8g+sY6nsOmUGwP/JQps0npeQ+akksDtwSY7p04YWyN0RvEDs0Ins"
    "UBJewBCSlJ59e9rZpumU9qSmj/LO2nPGwbpse4irE9yeZ3N2i1xXnwvXp+aCo0HhSsgKGnCN3t0E"
    "z6zRhPtaeM4e60VFMzlHqRQN3pKkz4p3kgG/l6TcwKQx9GwDknlBm/Q8x7qWqp5TZgCPPL30u6T8"
    "i1JFWHfhYUWTbAD87g0pUTL90AConVbGwTMnTGpN7pM5vAjOb1wF160Oro6qa3DBmNkMUV/LoRmy"
    "4Vj8V6VND1blXlGD1ILYIYlzBB0iuQaOb99DQyCBUesGJhi/pKNkeD5li4JH7yZBqcLzBPjSLhh"
    "LwESf5ewrqWq+5QYAO/amTB/kiqiugsPz9Y801GESilXMv0oX9lCURRObDiUPHPHeaM6182FZT25"
    "LQ+Q2xLB1THzMmlxOx7G2ZOAgUPgeGcPrDtOqDCloBG17qqA461dEPkDFYxn7gSYhaGRv2DXKCRq"
    "dO4EsFsEdq/ICEBJ0ZoEc4JgBU0IygiSXhxza0LQg4dJupZbMn9uKrrssgHklyzMp2nxr5TCY3ep"
    "oC8UBylLaEHid5IGliJT4IFOdshYMcAhRIOmfNOEZ3oJRWoiR3WCKZJkLO4LpsCYNwOWKjesO6th"
    "IWUXvLkWDEh5QbgteyrJMAimwkWuzmTy/6dB0jqBqgNHiGsUFDXynDMOyggID9MqyRACjRLIsEwE"
    "uUPkZ1Ofybyx0nFQOpYkQEAyIBI2SPFSKv7zji4bgAnj96RYJcnQ32lYHqVONGYFljTns+Ilg0JS"
    "X/zEoAugazBHFMH5zavh+uyC6K6OgHqn3zO9FK7PXQy9ygPb8gPQq5vBCkbVCl2kE9cxjF7TDPuq"
    "Q9CPtcF104Vwzx4LyRtZ5G5xOwUXIWrEG2rGmMEAK78kOvjlOAbmRgkkBtV4YUyyStaAgtEzHhAO"
    "dOOfhCxtbWj9TVe76JIB0GPoClL+W7pKRKraS9pAMoYNgMy0B1CqhSIteNX794HS2BnSHbDRgGZw"
    "0I1n5mg4v3wJhSajuzoEBmPIAHjOnQRj1iRohgOOf2yB5Uhtp1SBlchyrA6OV7fC0qzDmDmRcE+k"
    "NUQRgl0cYUj4o0Ze16gWnF+7HJ7Z/BoNYaEnF/PC9MXmOqiWdsAlt6O1hb80kmz9dZGvSfVIKIhW"
    "OnecohVTgUv5BdbBjm0SL+m0AfCXHIjFRxPvqnshPbTZ5P7aVdAuPheer3yKZs0xkKzAxGHSbg/N"
    "nCReCusY4NeM3Yumg5XLHrSBFcyNmWlTIU85oRTWI62wbquApexkpxQ/GC/nefh1MiLGaT3SAjly"
    "BPV1NnhdwfX+TtpdoyWwfrAF7ounwxyQrXhQvCieVIu4J+6TJww2NJZhJNnGRZI0AGlTxDbRyr3A"
    "VPsI66L3LvkzqUfyjbhFtaf5bkjQCozvejcZ5JqI887CgJWVyN1Zh4LVldDmzYJRUgze+eQBjUch"
    "CZLYIVXhWY98dJ5ZuZ1B/r52mPzybeUhG1gcyjRzM+G+YCrc818A27aTsK0/Aq22BSq8GK/DJOsZ"
    "p1bbCtumY7BtqYbnCgqhXnIWGUKW92lF+Jhejhrpu45CK6+CMXWUsg/mRb0Yx+sggmNe6RLzULho"
    "TcAyFPNmhsr2/JkwKPIVE0FPVUpMVLrYyf46ZQD8HyJImN/vZJ8pb2aOHozMfXVqsBk5D17W1irI"
    "YUUQiYw2N9KoFblKymB8bVjJXbQRZdlxGIIXlwQnaS1gjB1C7shkmNPGw3K0FRmvbVWKT9U9cmh1"
    "rRQ12g7rvnqYU8fBmDsJnonD6YnnHU6OGDHNnnPHg3lgogTzRAqtfsjjW0tweaxEElEyzNzT7sZx"
    "Wda2api81ojVuAfrWBdZJzvTpVdiSbZ0G/IJigKGxumSxJFScIrMyHBOWKGpPJF+JCsEu0s88wc1"
    "MMYPpW29LOh7j6tSsyAb7mvmAvmFsJY3wbr1BPTKRlXXGydel/652AAAEABJREFULDMNlrJGaPZc"
    "uK45F+ZA70+tmWblt08aFiCNlZefBKBFsmT5BGpiZEiGsguyjYE5ZVWsix5D/oIRJpvCWYvbXi06"
    "pLw2LmAPAui7j6J5dA48mRaY5OvytXF6IbRjNZBq1CMTw5OiZOWnmZ996GBQSTfui6bBuro3eA3B"
    "sO6LZsC25iisu6rAszDPtJEx91wp06DVO2HZXwP76iPwnDcZTCvTzK9huC6bCebFTxGxBY6GgRe5"
    "ZAYM668Lv3Kdduwkmsflhcp2SgFY5uHwvXnPwZi80QsWJUtDUgbAiw0SStosfP3MatUN0N5eg8a8"
    "NjQOBhpz26C9vhL8Cy6TIjOBUKa/gf/K2qCTCDq8CwSYgwtgjiqGdelWBW0W50FzC2gUfkSa/jFt"
    "ok3AHJSvKLSs3AmTdp6ZF1UQfHJ7AOadJ4Dgcl9e0lPCHDqAZOj0yjbX6ZVtngvaG6vAMveBps3F"
    "NOWvb0ryk4s0+onTrxYbvbbwFTEJ1Y/UQPtwM/DBeujvUjpUBVFdD1HXTIvhgTCzHR3b8y++KO4d"
    "CbMxaTi0AxXk2zerdgbtuFrXlal8Op+sGw/DM592nIlIrb4FOi3emRe6DTkUz+TyqTVBSA0Zf5Zd"
    "yUzUNysZ6mVVJNMNSrbah5ugl1eHtUiTW4mJ762v+EYy1CRsALzjS4+Z7yWDPFWw9NQhVN4zZSIe"
    "kh7n/FKa1uiEf8HKCz+tpQ36wUqYxbng0KGkGY8x8WsR4W6PHzHvHRjjh8G6Zo8qUsYjLTT7u9R9"
    "Op80fq3bsAYM3rpsO4zxtJZxdNyoZyNgGUh/dIhkw7zyOkIvqyZ+28AyZH5Zpixb3m3mX5ZxWVom"
    "KX+UN21+QaK0JWwAJjzflrQkTBRxKuF4oGLhkwxAA8yDHwmOB49nLVZ6c0g+JD8NaOaPBMtlMjcD"
    "IKXQjp/kW5gU9bHuqVL5vnCybjmqaGZa9co64oUMopD2BLggUnLRfgfJRLJsaPbXD9cAUeSjtdIk"
    "YLeFL9UiIuytu0pgUI0tboRGNsoCZmCLY0k7q2v+EYy1CRsALzjS4+Z7yWDPFWw9NQhVN4zZSIek"
    "h7n/FKa1uiEf8HKCz+tpQ36wUqYxbng0KGkGY8x8WsR4W6PHzHvHRjjh8G6Zo8qUsYjLTT7u9R9"
    "Op80fq3bsAYM3rpsO4zxtJZxdNyoZyNgGUh/dIhkw7zyOkIvqyZ+28AyZH5Zpixb3m3mX5ZxWVom"
    "KX+UN21+QaK0JWwAJjzflrQkTBRxKuF4oGLhkwxAA8yDHwmOB49nLVZ6c0g+JD8NaOaPBMtlMjcD"
    "IKXQjp/kW5gU9bHuqVL5vnCybjmqaGZa9co64oUMopD2BLggUnLRfgfJRLJsaPbXD9cAUeSjtdIk"
    "YLeFL9UiIuytu0pgUI0tboRGNsoCZmCLY0k7q2v+EYy1CRsALzjS4+Z7yWDPFWw9NQhVN4zZSIek"
    "h7n/FKa1uiEf8HKCz+tpQ36wUqYxbng0KGkGY8x8WsR4W6PHzHvHRjjh8G6Zo8qUsYjLTT7u9R9"
    "Op80fq3bsAYM3rpsO4zxtJZxdNyoZyNgGUh/dIhkw7zyOkIvqyZ+28AyZH5Zpixb3m3mX5ZxWVom"
    "KX+UN21+QaK0JWwAJjzflrQkTBRxKuF4oGLhkwxAA8yDHwmOB49nLVZ6c0g+JD8NaOaPBMtlMjcD"
    "IKXQjp/kW5gU9bHuqVL5vnCybjmqaGZa9co64oUMopD2BLggUnLRfgfJRLJsaPbXD9cAUeSjtdIk"
    "YLeFJRREFULDMNlrJGaPZcuK45F+ZA70+tmWblt08aFiCNlZefBKBFsmT5BGpiZEiGsguyjYE5ZV"
    "Wsix5D/oIRJpvCWYvbXi06pLw2LmAPAui7j6J5dA48mRaY5OvytXF6IbRjNZBq1CMTw5OiZOWnmZ"
    "996GBQSTfui6bBuro3eA3BsO6LZsC25iisu6rAszDPtJEx91wp06DVO2HZXwP76iPwnDcZTCvTzK9"
    "huC6bCebFTxGxBY6GgRe5ZAYM668Lv3Kdduwkmsflhcp2SgFY5uHwvXnPwZi80QsWJUtDUgbAiw0"
    "SStosfP3MatUN0N5eg8a8NjQOBhpz26C9vhL8Cy6TIjOBUKa/gf/K2qCTCDq8CwSYgwtgjiqGdel"
    "WBW0W50FzC2gUfkSa/jFtok3AHJSvKLSs3AmTdp6ZF1UQfHJ7AOadJ4Dgcl9e0lPCHDqAZOj0yjb"
    "X6ZVtngvaG6vAMveBps3FNOWvb0ryk4s0+onTrxYbvbbwFTEJ1Y/UQPtwM/DBeujvUjpUBVFdD1H"
    "XTIvhgTCzHR3b8y++KO4dCbMxaTi0AxXk2zerdgbtuFrXlal8Op+sGw/DM592nIlIrb4FOi3emRe"
    "6DTkUz+TyqTVBSA0Zf5ZdyUzUNysZ6mVVJNMNSrbah5ugl1eHtUiTW4mJ762v+EYy1CRsALzjS4+"
    "Z7yWDPFWw9NQhVN4zZSIekh7n/FKa1uiEf8HKCz+tpQ36wUqYxbng0KGkGY8x8WsR4W6PHzHvHR"
    "jjh8G6Zo8qUsYjLTT7u9R9Op80fq3bsAYM3rpsO4zxtJZxdNyoZyNgGUh/dIhkw7zyOkIvqyZ+28"
    "AyZH5Zpixb3m3mX5ZxWVomKX+UN21+QaK0JWwAJjzflrQkTBRxKuF4oGLhkwxAA8yDHwmOB49nL"
    "VZ6c0g+JD8NaOaPBMtlMjcDIKXQjp/kW5gU9bHuqVL5vnCybjmqaGZa9co64oUMopD2BLggUnLR"
    "fgfJRLJsaPbXD9cAUeSjtdIkYLeFJRREFULDMNlrJGaPZcuK45F+ZA70+tmWblt08aFiCNlZefBK"
    "BFsmT5BGpiZEiGsguyjYE5ZVWsix5D/oIRJpvCWYvbXi06pLw2LmAPAui7j6J5dA48mRaY5OvytX"
    "F6IbRjNZBq1CMTw5OiZOWnmZ996GBQSTfui6bBuro3eA3BsO6LZsC25iisu6rAszDPtJEx91wp06"
    "DVO2HZXwP76iPwnDcZTCvTzK9huC6bCebFTxGxBY6GgRe5ZAYM668Lv3Kdduwkmsflhcp2SgFY5u"
    "HwvXnPwZi80QsWJUtDUgbAiw0SStosfP3MatUN0N5eg8a8NjQOBhpz26C9vhL8Cy6TIjOBUKa/gf"
    "/K2qCTCDq8CwSYgwtgjiqGdelWBW0W50FzC2gUfkSa/jFtok3AHJSvKLSs3AmTdp6ZF1UQfHJ7AO"
    "adJ4Dgcl9e0lPCHDqAZOj0yjbX6ZVtngvaG6vAMveBps3FNOWvb0ryk4s0+onTrxYbvbbwFTEJ1Y"
    "/UQPtwM/DBeujvUjpUBVFdD1HXTIvhgTCzHR3b8y++KO4dCbMxaTi0AxXk2zerdgbtuFrXlal8Op"
    "+sGw/DM592nIlIrb4FOi3emRe6DTkUz+TyqTVBSA0Zf5ZdyUzUNysZ6mVVJNMNSrbah5ugl1eHt"
    "UiTW4mJ762v+AAAADlJREFUeNpjYBgFgx0AAIAAAQABnj9rnAAAAABJRU5ErkJggg=="
)

# ── i18n ─────────────────────────────────────────────────────────────────────

_I18N: dict[str, dict[str, str]] = {
    "es": {
        "report_title":         "Informe de Verificación",
        "generated_by":         "Sistema de Verificación Automática de Entregas",
        "section_release":      "Información de la entrega",
        "section_rules":        "Resultados de reglas",
        "field_release_name":   "Entrega",
        "field_release_version":"Versión",
        "field_release_id":     "ID de entrega",
        "field_verification_id":"ID de verificación",
        "field_executed_at":    "Ejecutado",
        "field_duration":       "Duración",
        "col_rule_id":          "Regla",
        "col_rule_name":        "Descripción",
        "col_status":           "Estado",
        "col_message":          "Detalle",
        "status_ok":            "Correcto",
        "status_error":         "Error",
        "status_warning":       "Advertencia",
        "status_no_evaluada":   "No evaluada",
        "status_unknown":       "No evaluada",
        "verdict_VALID":        "Válida",
        "verdict_INVALID":      "No válida",
        "verdict_WITH_WARNINGS":"Con advertencias",
        "verdict_NOT_EVALUATED":"No evaluada",
        "no_detail":            "Verificación superada",
        "duration_ms":          "ms",
        "na":                   "N/D",
        "footer_note":          "Generado automáticamente por SVAES",
        "summary_ok":           "correctas",
        "summary_errors":       "errores",
        "summary_warnings":     "advertencias",
        "summary_rules":        "reglas evaluadas",
        "rule_evidence.ok.default": "Regla superada correctamente.",
        "rule_evidence.ok.RV-01": "Se encontraron artefactos registrados en la entrega.",
        "rule_evidence.ok.RV-02": "Todos los IDs de artefactos son únicos y coherentes entre sí.",
        "rule_evidence.ok.RV-03": "Todos los artefactos de tipo tarea tienen un estado válido.",
        "rule_evidence.ok.RV-04": "Todos los campos de estimación y esfuerzo contienen valores numéricos correctos.",
        "rule_evidence.ok.RV-05": "Se encontraron los documentos requeridos en la entrega.",
        "rule_evidence.ok.RV-06": "Todos los documentos tienen su versión correctamente especificada.",
        "rule_evidence.ok.RV-07": "La release está correctamente registrada en el sistema de planificación.",
        "rule_evidence.ok.RV-08": "La planificación de la release es coherente con los artefactos registrados.",
        "rule_evidence.ok.RV-09": "Todas las referencias de código están correctamente vinculadas a la entrega.",
        "rule_evidence.ok.RV-10": "Se encontró el informe de pruebas con estado aprobatorio.",
        "rule_evidence.ok.has_duplicated_code": "No se detectó código duplicado por encima del umbral configurado.",
        "rule_evidence.ok.has_high_severity_vulnerabilities": "No se detectaron vulnerabilidades de alta severidad en el código.",
        "rule_evidence.ok.has_critical_vulnerabilities": "No se detectaron vulnerabilidades críticas en el código.",
        "rule_evidence.ok.has_open_high_priority_issues": "No hay issues de alta prioridad abiertos.",
        "rule_evidence.ok.has_code_smells": "No se detectaron code smells significativos.",
        "rule_evidence.ok.has_security_hotspots": "No se detectaron security hotspots en el código.",
        "rule_evidence.ok.has_uncovered_code": "La cobertura de tests se encuentra dentro del umbral aceptable.",
        "rule_evidence.ok.has_blocking_issues": "No se detectaron issues bloqueantes para esta entrega.",
        "rule_evidence.ok.meets_minimum_test_coverage": "La cobertura de tests supera el umbral mínimo requerido.",
        "rule_evidence.ok.meets_maximum_complexity": "La complejidad del código está dentro del límite máximo permitido.",
        "rule_evidence.ok.RV-07.found": "Marcador de registro externo '{{artifact_type}}' encontrado en artefacto '{{artifact_id}}'",
        "rule_evidence.ok.RV-10.found": "Artefacto '{{artifact_id}}' de tipo '{{artifact_type}}' encontrado con estado aprobatorio: '{{approved_status}}'",
        "rule_evidence.no_connector": "No hay conector configurado para esta regla. El resultado no pudo verificarse a través de una fuente de datos externa.",
        "rule_evidence.error.RV-01": "La lista de artefactos está vacía. Se requiere al menos un artefacto para proceder.",
        "rule_evidence.error.RV-02": "Referencias huérfanas detectadas: {{count}}. Los siguientes IDs referenciados en artefactos '{{source_type}}' no existen como '{{target_type}}': {{missing_refs}}",
        "rule_evidence.error.RV-03": "Artefactos con estado inválido (permitidos: {{allowed_states}}): {{invalid_artifacts}}",
        "rule_evidence.error.RV-04": "Artefactos con campos numéricos inválidos o negativos (campos: {{numeric_fields}}): {{invalid_artifacts}}",
        "rule_evidence.error.RV-05.no_docs": "No se encontraron artefactos de tipo '{{artifact_type}}'",
        "rule_evidence.error.RV-05.inaccessible": "Documentos inaccesibles (flag '{{accessible_field}}' no es true): {{inaccessible_docs}}",
        "rule_evidence.error.RV-06": "Artefactos con valor de '{{attribute}}' diferente a '{{expected_value}}': {{mismatched_artifacts}}",
        "rule_evidence.error.RV-07.not_found": "No se encontró artefacto marcador de tipo '{{artifact_type}}' que indique registro externo",
        "rule_evidence.error.RV-07.not_true": "Artefacto '{{artifact_id}}' de tipo '{{artifact_type}}' encontrado pero '{{marker_field}}' no es true",
        "rule_evidence.error.RV-08.master_not_found": "Artefacto maestro '{{master_id}}' no encontrado",
        "rule_evidence.error.RV-08.field_not_array": "Campo '{{master_field}}' en maestro '{{master_id}}' no es un array válido",
        "rule_evidence.error.RV-08.field_not_found": "Campo '{{master_field}}' no encontrado en artefacto maestro '{{master_id}}'",
        "rule_evidence.error.RV-08.discrepancy": "Discrepancia entre lista declarada y payload. IDs declarados en '{{master_field}}' del maestro '{{master_id}}' que no están en artefactos '{{target_type}}': {{missing_ids}}",
        "rule_evidence.error.RV-09": "Referencias inválidas o inaccesibles encontradas: {{invalid_refs}}",
        "rule_evidence.error.RV-10": "No se encontró artefacto de tipo '{{artifact_type}}' con estado aprobatorio (estados aceptados: {{approved_states}})",
        "rule_evidence.error.has_duplicated_code": "Artefactos con código duplicado excesivo: {{violations}}",
        "rule_evidence.error.has_high_severity_vulnerabilities": "Artefactos con vulnerabilidades de alta severidad: {{violations}}",
        "rule_evidence.error.has_critical_vulnerabilities": "Artefactos con vulnerabilidades críticas: {{violations}}",
        "rule_evidence.error.has_open_high_priority_issues": "Artefactos con issues de alta prioridad abiertos: {{violations}}",
        "rule_evidence.error.has_code_smells": "Artefactos con code smells: {{violations}}",
        "rule_evidence.error.has_security_hotspots": "Artefactos con hotspots de seguridad sin revisar: {{violations}}",
        "rule_evidence.error.has_uncovered_code": "Artefactos con código sin cobertura: {{violations}}",
        "rule_evidence.error.has_blocking_issues": "Artefactos con issues bloqueantes: {{violations}}",
        "rule_evidence.error.meets_minimum_test_coverage": "Artefactos que no alcanzan la cobertura mínima: {{violations}}",
        "rule_evidence.error.meets_maximum_complexity": "Artefactos que superan la complejidad máxima: {{violations}}",
        "rule_evidence.warning.artifact_fetch_error": "No se pudo obtener el artefacto '{{ref}}' (tipo: {{artifact_type}}) desde el conector '{{connector}}': {{error}}",
        "rule_evidence.warning.artifact_fetch_error.evidence": "No se pudo recuperar '{{ref}}' de tipo {{artifact_type}} desde el conector '{{connector}}'. Verifique que la referencia externa '{{ref}}' existe y es accesible con las credenciales configuradas.",
        "rule_evidence.no_evaluada.empty_artifacts": "No hay artefactos disponibles para evaluar esta regla.",
        "rule_evidence.no_evaluada.RV-06": "No se encontraron artefactos de tipo '{{artifact_type}}' para evaluar",
        "rule_evidence.no_evaluada.RV-07": "Parámetro 'artifact_type' no configurado — regla no aplicable",
        "rule_evidence.no_evaluada.RV-08": "Parámetro 'master_artifact_id' no proporcionado",
        "rule_evidence.no_evaluada.no_artifacts_of_type": "No hay artefactos de tipo '{{artifact_type}}' en la entrega — regla no aplicable",
    },
    "en": {
        "report_title":         "Verification Report",
        "generated_by":         "Automated Software Delivery Verification System",
        "section_release":      "Delivery information",
        "section_rules":        "Rule results",
        "field_release_name":   "Release",
        "field_release_version":"Version",
        "field_release_id":     "Release ID",
        "field_verification_id":"Verification ID",
        "field_executed_at":    "Executed",
        "field_duration":       "Duration",
        "col_rule_id":          "Rule",
        "col_rule_name":        "Description",
        "col_status":           "Status",
        "col_message":          "Detail",
        "status_ok":            "Passed",
        "status_error":         "Error",
        "status_warning":       "Warning",
        "status_no_evaluada":   "Not evaluated",
        "status_unknown":       "Not evaluated",
        "verdict_VALID":        "Valid",
        "verdict_INVALID":      "Invalid",
        "verdict_WITH_WARNINGS":"With warnings",
        "verdict_NOT_EVALUATED":"Not evaluated",
        "no_detail":            "Rule passed successfully",
        "duration_ms":          "ms",
        "na":                   "N/A",
        "footer_note":          "Automatically generated by SVAES",
        "summary_ok":           "passed",
        "summary_errors":       "errors",
        "summary_warnings":     "warnings",
        "summary_rules":        "rules evaluated",
        "rule_evidence.ok.default": "Rule passed successfully.",
        "rule_evidence.ok.RV-01": "Artifacts were found registered in the release.",
        "rule_evidence.ok.RV-02": "All artifact IDs are unique and consistent.",
        "rule_evidence.ok.RV-03": "All task-type artifacts have a valid status.",
        "rule_evidence.ok.RV-04": "All estimation and effort fields contain valid numeric values.",
        "rule_evidence.ok.RV-05": "The required documents were found in the release.",
        "rule_evidence.ok.RV-06": "All documents have their version correctly specified.",
        "rule_evidence.ok.RV-07": "The release is correctly registered in the planning system.",
        "rule_evidence.ok.RV-08": "The release planning is consistent with the registered artifacts.",
        "rule_evidence.ok.RV-09": "All code references are correctly linked to the release.",
        "rule_evidence.ok.RV-10": "The test report with approval status was found.",
        "rule_evidence.ok.has_duplicated_code": "No duplicate code detected above the configured threshold.",
        "rule_evidence.ok.has_high_severity_vulnerabilities": "No high-severity vulnerabilities detected in the code.",
        "rule_evidence.ok.has_critical_vulnerabilities": "No critical vulnerabilities detected in the code.",
        "rule_evidence.ok.has_open_high_priority_issues": "No open high-priority issues.",
        "rule_evidence.ok.has_code_smells": "No significant code smells detected.",
        "rule_evidence.ok.has_security_hotspots": "No security hotspots detected in the code.",
        "rule_evidence.ok.has_uncovered_code": "Test coverage is within the acceptable threshold.",
        "rule_evidence.ok.has_blocking_issues": "No blocking issues detected for this release.",
        "rule_evidence.ok.meets_minimum_test_coverage": "Test coverage exceeds the minimum required threshold.",
        "rule_evidence.ok.meets_maximum_complexity": "Code complexity is within the maximum allowed limit.",
        "rule_evidence.ok.RV-07.found": "External registration marker '{{artifact_type}}' found in artifact '{{artifact_id}}'",
        "rule_evidence.ok.RV-10.found": "Artifact '{{artifact_id}}' of type '{{artifact_type}}' found with approval status: '{{approved_status}}'",
        "rule_evidence.no_connector": "No connector configured for this rule. The result could not be verified through an external data source.",
        "rule_evidence.error.RV-01": "The artifact list is empty. At least one artifact is required to proceed.",
        "rule_evidence.error.RV-02": "Orphan references detected: {{count}}. The following IDs referenced in '{{source_type}}' artifacts do not exist as '{{target_type}}': {{missing_refs}}",
        "rule_evidence.error.RV-03": "Artifacts with invalid status (allowed: {{allowed_states}}): {{invalid_artifacts}}",
        "rule_evidence.error.RV-04": "Artifacts with invalid or negative numeric fields (fields: {{numeric_fields}}): {{invalid_artifacts}}",
        "rule_evidence.error.RV-05.no_docs": "No artifacts of type '{{artifact_type}}' found",
        "rule_evidence.error.RV-05.inaccessible": "Inaccessible documents (flag '{{accessible_field}}' is not true): {{inaccessible_docs}}",
        "rule_evidence.error.RV-06": "Artifacts with '{{attribute}}' value different from '{{expected_value}}': {{mismatched_artifacts}}",
        "rule_evidence.error.RV-07.not_found": "No marker artifact of type '{{artifact_type}}' found indicating external registration",
        "rule_evidence.error.RV-07.not_true": "Artifact '{{artifact_id}}' of type '{{artifact_type}}' found but '{{marker_field}}' is not true",
        "rule_evidence.error.RV-08.master_not_found": "Master artifact '{{master_id}}' not found",
        "rule_evidence.error.RV-08.field_not_array": "Field '{{master_field}}' in master '{{master_id}}' is not a valid array",
        "rule_evidence.error.RV-08.field_not_found": "Field '{{master_field}}' not found in master artifact '{{master_id}}'",
        "rule_evidence.error.RV-08.discrepancy": "Discrepancy between declared list and payload. IDs declared in '{{master_field}}' of master '{{master_id}}' that are not in '{{target_type}}' artifacts: {{missing_ids}}",
        "rule_evidence.error.RV-09": "Invalid or inaccessible references found: {{invalid_refs}}",
        "rule_evidence.error.RV-10": "No artifact of type '{{artifact_type}}' with approval status found (accepted states: {{approved_states}})",
        "rule_evidence.error.has_duplicated_code": "Artifacts with excessive duplicate code: {{violations}}",
        "rule_evidence.error.has_high_severity_vulnerabilities": "Artifacts with high-severity vulnerabilities: {{violations}}",
        "rule_evidence.error.has_critical_vulnerabilities": "Artifacts with critical vulnerabilities: {{violations}}",
        "rule_evidence.error.has_open_high_priority_issues": "Artifacts with open high-priority issues: {{violations}}",
        "rule_evidence.error.has_code_smells": "Artifacts with code smells: {{violations}}",
        "rule_evidence.error.has_security_hotspots": "Artifacts with unreviewed security hotspots: {{violations}}",
        "rule_evidence.error.has_uncovered_code": "Artifacts with uncovered code: {{violations}}",
        "rule_evidence.error.has_blocking_issues": "Artifacts with blocking issues: {{violations}}",
        "rule_evidence.error.meets_minimum_test_coverage": "Artifacts not meeting minimum coverage: {{violations}}",
        "rule_evidence.error.meets_maximum_complexity": "Artifacts exceeding maximum complexity: {{violations}}",
        "rule_evidence.warning.artifact_fetch_error": "Could not fetch artifact '{{ref}}' (type: {{artifact_type}}) from connector '{{connector}}': {{error}}",
        "rule_evidence.warning.artifact_fetch_error.evidence": "Could not retrieve '{{ref}}' of type {{artifact_type}} from connector '{{connector}}'. Verify that the external reference '{{ref}}' exists and is accessible with the configured credentials.",
        "rule_evidence.no_evaluada.empty_artifacts": "No artifacts available to evaluate this rule.",
        "rule_evidence.no_evaluada.RV-06": "No artifacts of type '{{artifact_type}}' found to evaluate",
        "rule_evidence.no_evaluada.RV-07": "'artifact_type' parameter not configured — rule not applicable",
        "rule_evidence.no_evaluada.RV-08": "'master_artifact_id' parameter not provided",
        "rule_evidence.no_evaluada.no_artifacts_of_type": "No artifacts of type '{{artifact_type}}' in the release — rule not applicable",
    },
}

_RULE_NAMES: dict[str, dict[str, str]] = {
    "es": {
        "RV-01": "Artefactos no vacíos",
        "RV-02": "Trazabilidad cruzada",
        "RV-03": "Estado de artefactos válido",
        "RV-04": "Campos numéricos válidos",
        "RV-05": "Documentos accesibles",
        "RV-06": "Versión consistente",
        "RV-07": "Registro externo marcado",
        "RV-08": "Artefactos maestros completos",
        "RV-09": "Referencias de origen válidas",
        "RV-10": "Documento con estado aprobatorio",
    },
    "en": {
        "RV-01": "Artifacts not empty",
        "RV-02": "Cross traceability check",
        "RV-03": "Artifact state validation",
        "RV-04": "Valid numeric fields",
        "RV-05": "Accessible documents",
        "RV-06": "Consistent version",
        "RV-07": "External registration marked",
        "RV-08": "Master artifacts complete",
        "RV-09": "Valid source references",
        "RV-10": "Document with approval status",
    },
}

# ── design tokens (exact per DESIGN.md) ──────────────────────────────────────

_INK         = (13/255,  15/255,  18/255)
_PAPER       = (246/255, 244/255, 240/255)
_PAPER2      = (237/255, 234/255, 228/255)
_ACCENT      = (232/255, 213/255, 163/255)
_BORDER      = (212/255, 207/255, 199/255)
_BORDER_STR  = (158/255, 152/255, 144/255)
_MUTED       = (122/255, 118/255, 112/255)

_VALID       = (42/255,  107/255, 60/255)
_VALID_BG    = (232/255, 245/255, 236/255)
_VALID_BDR   = (168/255, 213/255, 181/255)

_INVALID     = (139/255, 26/255,  26/255)
_INVALID_BG  = (250/255, 234/255, 234/255)
_INVALID_BDR = (216/255, 128/255, 128/255)

_WARN        = (139/255, 94/255,  0/255)
_WARN_BG     = (253/255, 243/255, 220/255)
_WARN_BDR    = (223/255, 192/255, 112/255)

_UNEVAL      = (90/255,  94/255,  101/255)
_UNEVAL_BG   = (235/255, 235/255, 235/255)
_UNEVAL_BDR  = (192/255, 192/255, 192/255)


def _t(lang: str, key: str) -> str:
    return _I18N.get(lang, _I18N["es"]).get(key, key)


def _translate_evidence(lang: str, evidence_key: str, params: dict | None = None) -> str:
    text = _t(lang, evidence_key)
    if params:
        for k, v in params.items():
            text = text.replace(f"{{{{{k}}}}}", str(v))
    return text


def _rule_name(lang: str, rule_id: str) -> str:
    return _RULE_NAMES.get(lang, _RULE_NAMES["es"]).get(rule_id, rule_id)


def _verdict_label(lang: str, verdict) -> str:
    verdict_str = verdict.value if hasattr(verdict, "value") else str(verdict)
    return _t(lang, f"verdict_{verdict_str}")


def _verdict_colors(verdict_str: str) -> tuple:
    v = verdict_str.upper()
    if v == "VALID":
        return _VALID, _VALID_BG, _VALID_BDR
    if v == "INVALID":
        return _INVALID, _INVALID_BG, _INVALID_BDR
    if "WARNING" in v:
        return _WARN, _WARN_BG, _WARN_BDR
    return _UNEVAL, _UNEVAL_BG, _UNEVAL_BDR


def _status_colors(status: str) -> tuple:
    s = (status or "").upper()
    if s == "OK":
        return _VALID, _VALID_BG, _VALID_BDR
    if s in ("ERROR", "FAILED"):
        return _INVALID, _INVALID_BG, _INVALID_BDR
    if s in ("WARNING", "WARN"):
        return _WARN, _WARN_BG, _WARN_BDR
    return _UNEVAL, _UNEVAL_BG, _UNEVAL_BDR


def _write_bytes(path: str, data: bytes) -> None:
    with open(path, "wb") as f:
        f.write(data)


def _write_csv(path: str, results: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)


_LOGO_PATH = "/app/static/images/icon-192.png"


class _HeaderFlowable(Flowable):
    def __init__(self, content_w: float, logo_sz: float, logo_off: float,
                 use_logo: bool, gen_date: str, lang: str):
        self._content_w = content_w
        self._logo_sz = logo_sz
        self._logo_off = logo_off
        self._use_logo = use_logo
        self._gen_date = gen_date
        self._lang = lang

    def wrap(self, aW: float, aH: float) -> tuple[float, float]:  # NOSONAR
        return self._content_w, self._logo_sz

    def draw(self):
        c = self.canv
        if self._use_logo:
            logo = Image(_LOGO_PATH, width=self._logo_sz, height=self._logo_sz)
            logo.drawOn(c, 0, 0)
        else:
            c.setFillColorRGB(*_ACCENT)
            c.rect(0, 4 * mm, 6, 6, fill=1, stroke=0)
        c.setFillColorRGB(*_INK)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(self._logo_off, 5 * mm, "SVAES")
        c.setFillColorRGB(*_MUTED)
        c.setFont("Helvetica", 6.5)
        c.drawString(self._logo_off, 1.5 * mm, _t(self._lang, "generated_by"))
        c.setFillColorRGB(*_MUTED)
        c.setFont("Helvetica", 7)
        c.drawRightString(self._content_w, 1.5 * mm, self._gen_date)
        c.setFillColorRGB(*_INK)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawRightString(self._content_w, 5 * mm, _t(self._lang, "report_title").upper())


class _VerdictBlock(Flowable):
    """Clean typographic verdict — thin left stripe, no colored fill."""

    _STRIPE = 3       # stripe width in points
    _PAD    = 4 * mm  # text left-offset from stripe
    _H      = 18 * mm # total height

    def __init__(self, content_w: float, verdict_text: str, result_id: str,
                 exec_at: str, fg):
        self._content_w  = content_w
        self._verdict_text = verdict_text
        self._result_id  = result_id
        self._exec_at    = exec_at
        self._fg         = fg

    def wrap(self, aW: float, aH: float) -> tuple[float, float]:  # NOSONAR
        return self._content_w, self._H

    def draw(self):
        c  = self.canv
        tx = self._STRIPE + self._PAD

        # thin left accent stripe
        c.setFillColorRGB(*self._fg)
        c.rect(0, 0, self._STRIPE, self._H, fill=1, stroke=0)

        # verdict text
        c.setFont("Helvetica-Bold", 15)
        c.drawString(tx, self._H * 0.50, self._verdict_text)

        # meta: truncated ID on left, execution date on right
        c.setFillColorRGB(*_MUTED)
        c.setFont("Courier", 7.5)
        c.drawString(tx, 2.5 * mm, self._result_id[:8] + "…")
        c.setFont("Helvetica", 8)
        c.drawRightString(self._content_w, 2.5 * mm, self._exec_at)


def _section_label(text: str, content_w: float, muted_c, border_c) -> list:
    return [
        Spacer(1, 5 * mm),
        Paragraph(
            text.upper(),
            ParagraphStyle("SL", fontName="Helvetica-Bold", fontSize=7,
                          textColor=muted_c, leading=9, spaceAfter=2 * mm),
        ),
        HRFlowable(width=content_w, thickness=0.5, color=border_c, spaceAfter=3 * mm),
    ]


def _build_rules_table(rules: list, ok_count: int, err_count: int, warn_count: int,
                        lang: str, content_w: float, muted_c, ink_c) -> tuple:
    n = len(rules)
    summary_line = (
        f"{n} {_t(lang, 'summary_rules')}  ·  "
        f"{ok_count} {_t(lang, 'summary_ok')}  ·  "
        f"{err_count} {_t(lang, 'summary_errors')}"
    )
    if warn_count:
        summary_line += f"  ·  {warn_count} {_t(lang, 'summary_warnings')}"

    th_s = ParagraphStyle("TH", fontName="Helvetica-Bold", fontSize=7,
                          textColor=muted_c, leading=9)
    tid_s = ParagraphStyle("TID", fontName="Courier", fontSize=7.5,
                          textColor=ink_c, leading=10)
    tnm_s = ParagraphStyle("TNM", fontName="Helvetica", fontSize=8,
                          textColor=ink_c, leading=11)
    tmg_s = ParagraphStyle("TMG", fontName="Helvetica", fontSize=7.5,
                          textColor=muted_c, leading=10)

    COL_ID  = 1.6 * cm
    COL_NM  = 7.0 * cm
    COL_ST  = 2.0 * cm
    COL_MSG = content_w - COL_ID - COL_NM - COL_ST

    data_rows = [[
        Paragraph(_t(lang, "col_rule_id").upper(), th_s),
        Paragraph(_t(lang, "col_rule_name").upper(), th_s),
        Paragraph(_t(lang, "col_status").upper(), th_s),
        Paragraph(_t(lang, "col_message").upper(), th_s),
    ]]

    for rule in rules:
        rule_id = rule.get("rule_id") or "–"
        status = (rule.get("status") or "").upper()
        evidence_key = rule.get("evidence") or rule.get("message")
        evidence_params = rule.get("evidence_params")
        if evidence_key is None or str(evidence_key).strip().lower() == "none":
            detail = _t(lang, "no_detail")
        else:
            detail = _translate_evidence(lang, evidence_key, evidence_params)
            if detail == evidence_key and status == "OK":
                detail = _t(lang, "no_detail")
        st_label = _t(lang, f"status_{status.lower()}") or status
        st_s = ParagraphStyle("ST", fontName="Helvetica", fontSize=8,
                             textColor=ink_c, leading=10)
        data_rows.append([
            Paragraph(rule_id, tid_s),
            Paragraph(_rule_name(lang, rule_id), tnm_s),
            Paragraph(st_label, st_s),
            Paragraph(detail, tmg_s),
        ])

    rules_table = Table(data_rows, colWidths=[COL_ID, COL_NM, COL_ST, COL_MSG], repeatRows=1)
    rules_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(*_PAPER2)),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.Color(*_BORDER_STR)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.Color(*_BORDER)),
    ]))

    summary_para = Paragraph(
        summary_line,
        ParagraphStyle("Sum", fontName="Helvetica", fontSize=8,
                      textColor=muted_c, leading=11, spaceAfter=4 * mm),
    )
    return summary_para, rules_table


def _build_pdf(pdf_path: str, result, release, lang: str) -> None:
    PAGE_W, _ = A4
    MARGIN    = 2.0 * cm
    CONTENT_W = PAGE_W - 2 * MARGIN

    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4,
        rightMargin=MARGIN, leftMargin=MARGIN,
        topMargin=1.5 * cm, bottomMargin=2.0 * cm,
        title=_t(lang, "report_title"), author="SVAES",
    )

    # ── computed values ───────────────────────────────────────────────────────
    verdict_str  = result.verdict.value if hasattr(result.verdict, "value") else str(result.verdict)
    verdict_text = _verdict_label(lang, result.verdict)
    fg_v, _, _ = _verdict_colors(verdict_str)

    rules      = result.rule_results or []
    ok_count   = sum(1 for r in rules if (r.get("status") or "").upper() == "OK")
    err_count  = sum(1 for r in rules if (r.get("status") or "").upper() in ("ERROR", "FAILED"))
    warn_count = sum(1 for r in rules if (r.get("status") or "").upper() in ("WARNING", "WARN"))

    r_name    = getattr(release, "name",    None) or _t(lang, "na")
    r_version = getattr(release, "version", None) or _t(lang, "na")
    exec_at   = (
        result.executed_at.strftime("%d/%m/%Y %H:%M UTC")
        if result.executed_at else _t(lang, "na")
    )
    duration  = f"{result.duration_ms} {_t(lang, 'duration_ms')}"
    gen_date  = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    muted_c = colors.Color(*_MUTED)
    ink_c   = colors.Color(*_INK)
    border_c = colors.Color(*_BORDER)

    _use_logo = os.path.isfile(_LOGO_PATH)
    LOGO_SZ   = 14 * mm
    LOGO_OFF  = (LOGO_SZ + 3 * mm) if _use_logo else 0

    # ── story ─────────────────────────────────────────────────────────────────
    story: list = []

    story.append(_HeaderFlowable(CONTENT_W, LOGO_SZ, LOGO_OFF, _use_logo, gen_date, lang))
    story.append(HRFlowable(
        width=CONTENT_W, thickness=0.5, color=border_c,
        spaceBefore=3 * mm, spaceAfter=5 * mm,
    ))

    story.append(Paragraph(
        _t(lang, "report_title"),
        ParagraphStyle("Title", fontName="Times-Roman", fontSize=22,
                      textColor=ink_c, leading=26, spaceAfter=2 * mm),
    ))

    story.append(Paragraph(
        f"{r_name}  ·  {r_version}  ·  {_t(lang, 'field_executed_at')}: {exec_at}",
        ParagraphStyle("Meta", fontName="Helvetica", fontSize=8,
                      textColor=muted_c, leading=11, spaceAfter=4 * mm),
    ))

    story.append(HRFlowable(
        width=CONTENT_W, thickness=0.5, color=border_c, spaceAfter=0,
    ))
    story.append(_VerdictBlock(CONTENT_W, verdict_text, str(result.id), exec_at, fg_v))
    story.append(HRFlowable(
        width=CONTENT_W, thickness=0.5, color=border_c, spaceAfter=5 * mm,
    ))

    # ── Delivery info ─────────────────────────────────────────────────────────
    story.extend(_section_label(_t(lang, "section_release"), CONTENT_W, muted_c, border_c))

    lbl_s = ParagraphStyle("Lbl", fontName="Helvetica-Bold", fontSize=7, textColor=muted_c, leading=9)
    val_s = ParagraphStyle("Val", fontName="Helvetica", fontSize=8.5, textColor=ink_c, leading=11)
    mon_s = ParagraphStyle("Mon", fontName="Courier", fontSize=8, textColor=ink_c, leading=11)

    C1, C2 = CONTENT_W * 0.28, CONTENT_W * 0.72

    def _info(label, value, mono=False):
        return [
            Paragraph(label, lbl_s),
            Paragraph(str(value) if value else _t(lang, "na"), mon_s if mono else val_s),
        ]

    info_data = [
        _info(_t(lang, "field_release_name"),    r_name),
        _info(_t(lang, "field_release_version"), r_version),
        _info(_t(lang, "field_release_id"),      str(result.release_id), mono=True),
        _info(_t(lang, "field_verification_id"), str(result.id),         mono=True),
        _info(_t(lang, "field_executed_at"),     exec_at),
        _info(_t(lang, "field_duration"),        duration),
    ]
    info_table = Table(info_data, colWidths=[C1, C2])
    info_table.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW",     (0, 0), (-1, -2), 0.5, border_c),
    ]))
    story.append(info_table)

    # ── Rules ─────────────────────────────────────────────────────────────────
    story.extend(_section_label(_t(lang, "section_rules"), CONTENT_W, muted_c, border_c))
    summary_para, rules_table = _build_rules_table(
        rules, ok_count, err_count, warn_count, lang, CONTENT_W, muted_c, ink_c,
    )
    story.append(summary_para)
    story.append(rules_table)

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=border_c, spaceAfter=3 * mm))
    story.append(Paragraph(
        f"SVAES  ·  {_t(lang, 'footer_note')}  ·  {gen_date}",
        ParagraphStyle("Foot", fontName="Helvetica", fontSize=7.5,
                      textColor=muted_c, leading=10, alignment=1),
    ))

    doc.build(story)


class ExportService(IExportService):

    def __init__(
        self,
        release_repository: IReleaseRepository,
        verification_repository: IVerificationResultRepository,
        project_repository: IProjectRepository,
    ):
        self._release_repo       = release_repository
        self._verification_repo  = verification_repository
        self._project_repo       = project_repository

    async def export_verification_to_pdf(
        self, release_id: UUID, result_id: UUID, lang: str = "es"
    ) -> str:
        result = await self._verification_repo.find_by_id(result_id)
        if not result:
            raise ValueError(f"Verificación no encontrada: {result_id}")

        release   = await self._release_repo.get_by_id(release_id)
        safe_lang = lang if lang in ("es", "en") else "es"
        pdf_path  = os.path.join(
            tempfile.gettempdir(), f"verification_{result_id}_{safe_lang}.pdf"
        )

        await asyncio.to_thread(_build_pdf, pdf_path, result, release, safe_lang)
        _log.info("PDF exported: result_id=%s lang=%s path=%s", result_id, safe_lang, pdf_path)
        return pdf_path

    async def export_project_results_to_csv(self, project_id: UUID) -> str:
        project = await self._project_repo.get_by_id(project_id)
        if not project:
            raise ValueError(f"Proyecto no encontrado: {project_id}")

        releases = await self._release_repo.list_by_project(project_id)
        results  = []
        for release in releases:
            for ver in await self._verification_repo.find_by_release(release.id):
                results.append({
                    "release_id":       str(release.id),
                    "release_name":     release.name,
                    "release_version":  release.version,
                    "verification_id":  str(ver.id),
                    "verdict":          ver.verdict,
                    "executed_at":      ver.executed_at.isoformat() if ver.executed_at else "",
                })

        csv_path = os.path.join(
            tempfile.gettempdir(), f"project_{project_id}_results.csv"
        )
        await asyncio.to_thread(_write_csv, csv_path, results)
        _log.info("CSV exported: project_id=%s path=%s count=%d", project_id, csv_path, len(results))
        return csv_path
