import jwt


class Encrypt:

    def __init__(self, encryptCfg):
        self.secretCfg = encryptCfg

    def encode(self, pwd):
        return jwt.encode(pwd, self.secretCfg['secret_key'], algorithm=self.secretCfg['algorithms'])

    def decode(self, pwd):
        return jwt.decode(pwd, self.secretCfg['secret_key'], algorithms=[self.secretCfg['algorithms']])
