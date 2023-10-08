from algo.models import Algo


class Algorithm:
    name = 'generic'

    def __init__(self, algo: Algo = None):
        self.algo = algo

    def save(self):
        self.algo.save()
