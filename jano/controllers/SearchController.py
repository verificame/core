import _thread
import os
from queue import Queue

from jano.exceptions import NoAzureKey, JunoException
from jano.search.bing import BingCrawler
from jano.search.google import GoogleCrawler


class SearchController(object):
    __results = []

    def bing_wrapper(self, query: str, q: Queue):
        bing = BingCrawler(os.environ.get('MS_BING_KEY'), "")
        values = bing.search_relatives(query)
        q.put(values)
        q.task_done()

    def google_wrapper(self, query: str, q: Queue):
        google = GoogleCrawler("")
        values = google.search_relatives(query)
        q.put(values)
        q.task_done()

    def search(self, query):
        try:
            if not os.environ.get('MS_BING_KEY'):
                raise NoAzureKey("Uma chave do Bing deve estar em MS_BING_KEY")
            q1, q2 = Queue(), Queue()
            _thread.start_new_thread(self.google_wrapper, (query, q1))
            _thread.start_new_thread(self.bing_wrapper, (query, q2))
            q1.join()
            q2.join()
            result = [q1.get(), q2.get()]
            return result
        except Exception as e:
            raise JunoException(e.__str__())
