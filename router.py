import requests, re, xml.dom.minidom, base64, json
from hashlib import sha256
from bs4 import BeautifulSoup
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

print_json = lambda a : print(json.dumps(a, indent=4))

class Crypter :

        def getSessToken(session, ip) :
            path = "/?_type=menuView&_tag=wlanAdvanced&Menu3Location=0"
            view_token = session.get("{}{}".format(ip, path))
            hex_token = re.search(r"_sessionTmpToken = \"(.*)\";", view_token.text).group(1)
            return "".join( chr(int(x,16)) for x in hex_token.split("\\x") if x )

        def asyEncode(query:str) :

            Srcstr = sha256(query.encode()).hexdigest()

            pubKey = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAodPTerkUVCYmv28SOfRV\n7UKHVujx/HjCUTAWy9l0L5H0JV0LfDudTdMNPEKloZsNam3YrtEnq6jqMLJV4ASb\n1d6axmIgJ636wyTUS99gj4BKs6bQSTUSE8h/QkUYv4gEIt3saMS0pZpd90y6+B/9\nhZxZE/RKU8e+zgRqp1/762TB7vcjtjOwXRDEL0w71Jk9i8VUQ59MR1Uj5E8X3WIc\nfYSK5RWBkMhfaTRM6ozS9Bqhi40xlSOb3GBxCmliCifOJNLoO9kFoWgAIw5hkSIb\nGH+4Csop9Uy8VvmmB+B3ubFLN35qIa5OG5+SDXn4L7FeAA5lRiGxRi8tsWrtew8w\nnwIDAQAB\n-----END PUBLIC KEY-----";

            # Convert the public key to RSA format
            rsa_key = RSA.import_key(pubKey)

            cipher = PKCS1_v1_5.new(rsa_key)
            encrypted = cipher.encrypt(Srcstr.encode())

            dstStr = base64.b64encode(encrypted).decode()

            if len(dstStr) == 0 or dstStr == "false":
                print("encrypt key fail!")
                dstStr = ""

            return dstStr

class Router :

    def __init__(self, ip : str, username : str, password : str) :
        self.session = requests.Session()
        self.ip = "http://{}".format(ip)
        self.username = username
        self.password = password
        self.Login()


    def Login(self) :

        def getPassword() :
            req = self.session.get("{}/?_type=loginData&_tag=login_token".format(self.ip))
            login_token = re.search(r"\d+",req.text).group(0)
            password = "{}{}".format(self.password, login_token)
            return sha256(password.encode()).hexdigest()

        data = {
            "action" : "login",
            "Username" : self.username,
            "Password" : "{}".format(getPassword()),
        }

        status = self.session.post("{}/?_type=loginData&_tag=login_entry".format(self.ip), data = data)

        if "failed" in status.text : raise Exception("Login Error!")

    def getBanList(self, query:str = None) :
        path = "/?_type=menuView&_tag=wlanAdvanced&Menu3Location=0"
        self.session.get("{}{}".format(self.ip, path))
        ban_list = self.session.get("{}/?_type=menuData&_tag=wlan_macfilterrule_lua.lua".format(self.ip))

        ban_dict = { "Account" : list() }

        if ban_list.ok :
            ban_list_dom = xml.dom.minidom.parseString(ban_list.text)
            instances = ban_list_dom.getElementsByTagName("Instance")

            for instance in instances :
                key = instance.getElementsByTagName("ParaName")
                value = instance.getElementsByTagName("ParaValue")
                valueToFind = instance.getElementsByTagName("ParaValue").item(2).firstChild.data
                result = dict()


                if query :
                    if valueToFind == query :
                        for k,v in zip(key,value) :
                            result[k.firstChild.data] = v.firstChild.data
                        ban_dict["Account"].append(result)
                        break
                else :
                    for k,v in zip(key,value) :
                        result[k.firstChild.data] = v.firstChild.data
                    ban_dict["Account"].append(result)

        if not ban_dict["Account"] :
            raise Exception("Account Not Found!")

        return ban_dict

    def ban(self, name:str, macId:str) :

        sess_token = Crypter.getSessToken(self.session, self.ip)

        data = {
            'IF_ACTION': 'Apply',
            '_InstID': '-1',
            'MACAddress': '{}'.format(macId),
            'Name': '{}'.format(name),
            'Interface': 'DEV.WIFI.AP1',
            'Btn_cancel_MACFilterRule': '',
            'Btn_apply_MACFilterRule': '',
            '_sessionTOKEN' : '{}'.format(sess_token)
        }

        query = "&".join("{}={}".format(k, v.replace(":", "%3A") if v == macId else v) for k, v in data.items() )

        headers = {
            "Check" : "{}".format(Crypter.asyEncode(query)),
        }

        path = "/?_type=menuData&_tag=wlan_macfilterrule_lua.lua"
        new_device = self.session.post("{}{}".format(self.ip, path), data=data, headers=headers)

        if re.search("<IF_ERRORSTR>FAIL", new_device.text) :
            raise Exception("Failed to ban Account !")

        return {
            "Name" : name,
            "MacAddress" : macId,
            "Status" : "Sukses Ban!"
        }

    def unban(self, uban_type:str, val:str) :

        if uban_type == "name" :
            data_device = self.getBanList(val).get("Account")
        elif uban_type == "mac" :
            data_device = tuple(filter(lambda akun : akun["MACAddress"] == val ,self.getBanList().get("Account")))
        else :
            raise Exception("Unknown Type!")

        data_device = data_device[0] if data_device else data_device

        if not data_device :
            raise Exception("Account not found!")

        sess_token = Crypter.getSessToken(self.session, self.ip)
        instId = data_device.get("_InstID")
        macId = data_device.get("MACAddress")
        name = data_device.get("Name")

        data = {
            'IF_ACTION': 'Delete',
            '_InstID': '{}'.format(instId),
            'MACAddress': '{}'.format(macId),
            'Name': '{}'.format(name),
            'Interface': 'DEV.WIFI.AP1',
            'Btn_cancel_MACFilterRule': '',
            'Btn_apply_MACFilterRule': '',
            '_sessionTOKEN' : '{}'.format(sess_token)
        }

        query = "&".join("{}={}".format(k, v.replace(":", "%3A") if v == macId else v) for k, v in data.items() )
        headers = {
            "Check" : "{}".format(Crypter.asyEncode(query)),
        }

        path = "/?_type=menuData&_tag=wlan_macfilterrule_lua.lua"
        unban_device = self.session.post("{}{}".format(self.ip, path), data=data, headers=headers)

        return {
            "Name" : name,
            "MacAddress" : macId,
            "Status" : "Sukses Un-Ban!"
        }

# if __name__ == "__main__" :
    # MyRouter = Router("192.168.1.1", "admin", "Telkomdso123")
    # data_akun = MyRouter.getBanList()
    # print(data_akun)
    # MyRouter.ban("putris","GC:31:31:31:31:34")
    # MyRouter.unban("name","peler")
    # mac = "32:31:31:31:31:34"
    # MyRouter.unban("mac", mac)
