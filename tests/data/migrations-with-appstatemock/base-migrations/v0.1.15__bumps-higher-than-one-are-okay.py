def up(self):
    appstate = self.ctx['appstate']
    data = appstate.get_data() or []
    data.append('up to v0.1.15')
    appstate.set_data(data)


def down(self):
    appstate = self.ctx['appstate']
    data = appstate.get_data() or []
    data.append('down from v0.1.15')
    appstate.set_data(data)
