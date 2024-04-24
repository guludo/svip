# SPDX-License-Identifier: MPL-2.0
def up(self):
    appstate = self.ctx['appstate']
    data = appstate.get_data() or []
    data.append('up to v1.3.0')
    appstate.set_data(data)
    raise Exception('exception in up() on purpose')


def down(self):
    appstate = self.ctx['appstate']
    data = appstate.get_data() or []
    data.append('down from v1.3.0')
    appstate.set_data(data)
    raise Exception('exception in down() on purpose')
