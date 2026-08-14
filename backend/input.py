class InputDevice:
    """Abstraction over a single touch input.

    Identified by ``input_id``. For this MVP the input is triggered through
    the HTTP route (``/api/touch``). A future hardware driver can subclass
    this and keep the same interface.
    """

    def __init__(self, input_id: int):
        self.input_id = input_id
