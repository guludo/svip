# SPDX-License-Identifier: MPL-2.0
def up(self):
    appstate = self.ctx['appstate']
    if 'events' in self.ctx:
        reached_wait_point, finished_test = self.ctx['events']
        reached_wait_point.set()
        has_finished_test = finished_test.wait(1)
        if not has_finished_test:
            raise RuntimeError('finished_test event not set: you should wrap the test code in a "try" block and set the event and join the thread in the "finally" clause')
    data = appstate.get_data() or []
    data.append('up to v1.3.0')
    appstate.set_data(data)
