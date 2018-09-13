
import os
import json
import tempfile
from collections import namedtuple

from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.plugins.callback import CallbackBase



class ResultCallback(CallbackBase):
    """A sample callback plugin used for performing an action as results come in

      If you want to collect all results into a single object for processing at
      the end of the execution, look into utilizing the ``json`` callback plugin
      or writing your own custom callback plugin
      """

    def __init__(self,display = None,option = None):
        super().__init__(display, option)
        self.result = None
        self.error_msg = None

    def __str__(self):
        pass

    #注：stderr这个是标准错误
    def v2_runner_on_ok(self, result):
        """Print a json representation of the result
                This method could store the result in an instance attribute for retrieval later
                """
        res = getattr(result, '_result')
        self.result = res
        self.error_msg = res.get('stderr')

    def v2_runner_on_failed(self, result, ignore_errors=None):
        if ignore_errors:
            return
        res = getattr(result, '_result')
        self.error_msg = res.get('stderr', '') + res.get('msg')

    def runner_on_unreachable(self, host, result):
        if result.get('unreachable'):
            self.error_msg = host + ':' + result.get('msg', '')

    def v2_runner_item_on_failed(self, result):
        res = getattr(result, '_result')
        self.error_msg = res.get('stderr', '') + res.get('msg')



class AnsibleTask(object):

    def __init__(self,hosts:list,forks=10,sources=[]):
        #用来加载yml文件或json内容，并支持vault的解密
        self.loader = DataLoader()
        self.passwords = dict(vault_pass = 'secret')

        # self.shell_result = []
        self.result_callback = ResultCallback()
        self.Options = None
        self.options = None

        self.hosts = hosts
        self.hosts_file = '/etc/ansible/hosts'#直接None也可以，此处执行的是传入的hosts，生成临时文件
        self.generate_hosts_file()

        sources.append(self.hosts_file)
        self.sources = sources
        self.inventory = InventoryManager(loader=self.loader,sources=self.sources)

        # host = self.inventory.get_host(hostname='10.12.248.90')
        # if host is None:
        #     raise '000'

        #管理变量的类，包括主机，组，变量等
        self.variable_manager = VariableManager(loader=self.loader,inventory=self.inventory)

        self.forks = forks


    #此处定义的方法主要是为了生成临时文件，防止程序读取sources=['/etc/ansible/hosts']被拒绝
    def generate_hosts_file(self):
        self.hosts_file = tempfile.mktemp()
        with open(self.hosts_file, 'w+', encoding='utf-8') as file:
            for host in self.hosts:
                file.write(host+'\n')
        # with open(self.hosts_file,'r') as f:
        #     ret = f.read()
        #     print(ret)


    def run_playbook(self,playbooks:list,extra_vars:dict):
        self.Options = namedtuple('Options',
                             ['listtags',
                              'listtasks',
                              'listhosts',
                              'syntax',
                              'connection',
                              'module_path',
                              'forks',
                              'remote_user',
                              'private_key_file',
                              'ssh_common_args',
                              'ssh_extra_args',
                              'sftp_extra_args',
                              'scp_extra_args',
                              'become',
                              'become_method',
                              'become_user',
                              'verbosity',
                              'check',
                              'host_key_checking',
                              'diff'])
        self.options = self.Options(listtags=False,
                                    listtasks=False,
                                    listhosts=False,
                                    syntax=False,
                                    connection='ssh',
                                    module_path=None,
                                    forks=10,
                                    remote_user='root',#此处必须设置为root启动，否则远程via ssh失败
                                    private_key_file='/home/parallels/.ssh/id_rsa',
                                    ssh_common_args=None,
                                    ssh_extra_args=None,
                                    sftp_extra_args=None,
                                    scp_extra_args=None,
                                    become=True,
                                    become_method='sudo',
                                    become_user='root',
                                    verbosity=3,
                                    check=False,
                                    host_key_checking=False,
                                    diff=False)#diff参数必须包含，否则直接抛出异常不报错退出正在执行的程序
        for i in playbooks:
            if not os.path.exists(i):
                print('[INFO] The [%s] playbook does not exist' % i)
        try:

            executor = PlaybookExecutor(playbooks=playbooks, inventory=self.inventory,
                                        variable_manager=self.variable_manager, loader=self.loader,
                                        options=self.options,passwords=self.passwords)

            setattr(getattr(executor, '_tqm'), '_stdout_callback', self.result_callback)
            result = executor.run()#此处执行结果仅0，1区分


        except Exception as e:
            return None,e

    def __del__(self):#此处析构函数删除生成的临时文件
        if self.hosts_file:
            os.remove(self.hosts_file)




if __name__ == '__main__':

    hosts = ['10.12.248.90']
    test_exe = AnsibleTask(hosts,forks=5)

    extra_vars = {}
    # playbooks = ['/home/parallels/Desktop/3.5demo/install.yml']

    #执行playbooks可以传入多个yml文件，但是仅仅返回最后一个执行结果，需要对callback进行操作以达到将所有执行结果显示
    playbooks = ['/home/parallels/Desktop/3.5demo/test.yml','/home/parallels/Desktop/3.5demo/init.yml']
    test_exe.run_playbook(playbooks,extra_vars)

    print(test_exe.sources,test_exe.result_callback.result)































