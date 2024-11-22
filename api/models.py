"""
Править файл на сервере S2
После правки этого файла сделать ./1restart
"""
from __future__ import absolute_import
import random

class JSONRPC(object):

    """
    JSONRPC(method="user_typing", params={"status":1}) # notification
    JSONRPC(id=0, method="get_version") # request w/o params
    JSONRPC(id=0, method="txt", params={"msg":"Hello World!"}) # request w/params
    JSONRPC(id=0, method="txt", params={"msg":"Hello World!"}) # request w/params
    JSONRPC(id=123456, result="done") # response on 123456 request
    JSONRPC(id=123457, error={"code": 1, "message": "Invalid Request"}) # error
    """

    def __init__(self, id=False, method=None, params=None, result=None, error=None, from_dict=None, **kwargs):
        if id == True:
            self.id = int(random.random() * 1e6)
            # self.id = int(random.random() * 4294967295)
        elif id == False:
            self.id = False
        else:
            self.id = id
        self.method = method
        self.params = params
        self.result = result
        self.error = error

        if from_dict:
            self.method = from_dict.get('method')
            self.result = from_dict.get('result')
            self.error = from_dict.get('error')
            self.params = from_dict.get('params')

    def render(self):  # returns dict!
        d = {"jsonrpc": 2.0}
        if self.id is not False:
            d['id'] = self.id
        if self.method is not None:
            d['method'] = self.method
            if self.params is not None:
                d['params'] = self.params
        elif self.result is not None and self.result != {}:
            d['result'] = self.result
        elif self.error is not None:
            d['error'] = self.error
        return d

    def __str__(self):
        return str(self.render())

    def __repr__(self):
        return "JSONRPC: " + str(self.render())

    # def add_actions(self, actions=None):
    #     self.params['actions'].update(dict(
    #         actions=actions
    #     ))

    # def set_error(self, error):
    #     self.add_to_reponse(error=dict(
    #         code=error.code,
    #         message=error.get_message(),
    #         status=error.status
    #     ))