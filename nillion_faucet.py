import os # noqa
import sys # noqa
import argparse
import random
import time
import copy
from datetime import datetime, timedelta

from DrissionPage import ChromiumOptions
from DrissionPage import ChromiumPage
from DrissionPage._elements.none_element import NoneElement

from fun_utils import ding_msg
from fun_utils import get_date
from fun_utils import load_file
from fun_utils import save2file
from fun_utils import conv_time
from fun_utils import time_difference

from conf import DEF_LOCAL_PORT
from conf import DEF_USE_HEADLESS
from conf import DEF_DEBUG
from conf import DEF_PATH_USER_DATA
from conf import DEF_DING_TOKEN
from conf import DEF_PATH_BROWSER
from conf import DEF_PATH_DATA_STATUS
from conf import DEF_HEADER_STATUS

from conf import DEF_PATH_DATA_PURSE
from conf import DEF_HEADER_PURSE

from conf import logger

"""
2024.11.04

"""


class NillionTask():
    def __init__(self) -> None:
        self.file_status = f'{DEF_PATH_DATA_STATUS}/status.csv'
        self.args = None
        self.page = None
        self.s_today = get_date(is_utc=True)

        self.n_points_spin = -1
        self.n_points = -1
        self.n_referrals = -1
        self.n_completed = -1

        # 是否有更新
        self.is_update = False

        # 账号执行情况
        self.dic_status = {}

        self.dic_purse = {}

        self.purse_load()

    def set_args(self, args):
        self.args = args
        self.is_update = False

        self.n_points_spin = -1
        self.n_points = -1
        self.n_referrals = -1
        self.n_completed = -1

    def __del__(self):
        self.status_save()
        # logger.info(f'Exit {self.args.s_profile}')

    def purse_load(self):
        self.file_purse = f'{DEF_PATH_DATA_PURSE}/purse.csv'
        self.dic_purse = load_file(
            file_in=self.file_purse,
            idx_key=0,
            header=DEF_HEADER_PURSE
        )

    def status_load(self):
        self.dic_status = load_file(
            file_in=self.file_status,
            idx_key=0,
            header=DEF_HEADER_STATUS
        )

    def status_save(self):
        save2file(
            file_ot=self.file_status,
            dic_status=self.dic_status,
            idx_key=0,
            header=DEF_HEADER_STATUS
        )

    def close(self):
        # 在有头浏览器模式 Debug 时，不退出浏览器，用于调试
        if DEF_USE_HEADLESS is False and DEF_DEBUG:
            pass
        else:
            self.page.quit()

    def initChrome(self, s_profile):
        """
        s_profile: 浏览器数据用户目录名称
        """
        profile_path = s_profile

        co = ChromiumOptions()

        # 设置本地启动端口
        co.set_local_port(port=DEF_LOCAL_PORT)
        if len(DEF_PATH_BROWSER) > 0:
            co.set_paths(browser_path=DEF_PATH_BROWSER)
        # co.set_paths(browser_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome') # noqa

        # 阻止“自动保存密码”的提示气泡
        co.set_pref('credentials_enable_service', False)

        # 阻止“要恢复页面吗？Chrome未正确关闭”的提示气泡
        co.set_argument('--hide-crash-restore-bubble')

        co.set_user_data_path(path=DEF_PATH_USER_DATA)
        co.set_user(user=profile_path)

        # https://drissionpage.cn/ChromiumPage/browser_opt
        co.headless(DEF_USE_HEADLESS)
        co.set_user_agent(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36') # noqa

        try:
            self.page = ChromiumPage(co)
        except Exception as e:
            logger.info(f'Error: {e}')
        finally:
            pass

    def update_status(self, avail_claim_ts):
        claim_time = conv_time(avail_claim_ts, 2)
        if self.args.s_profile in self.dic_status:
            self.dic_status[self.args.s_profile][1] = claim_time
        else:
            self.dic_status[self.args.s_profile] = [
                self.args.s_profile,
                claim_time
            ]

    def faucet_claim(self, s_purse):
        """
        登录及校验是否登录成功
        """
        self.page.get('https://faucet.testnet.nillion.com/')
        self.page.refresh()
        self.page.wait.load_start()

        for i in range(1, 3):
            logger.info(f'Nillion Claim try_i={i}/10')

            # Step One
            s_path = '@@class:v-btn__content@@text():Start'
            self.page.wait.eles_loaded(f'{s_path}')
            self.page.actions.move_to(f'{s_path}')
            button = self.page.ele(f'{s_path}', timeout=2)
            if isinstance(button, NoneElement):
                logger.info('Step One: Not Found ...')
                continue
            else:
                logger.info('Step One: Click ...')
                button.click(by_js=True)
                self.page.wait(2)

                ele_input = self.page.ele('@id=input-34', timeout=2)
                if not isinstance(ele_input, NoneElement):
                    logger.info('Enter a wallet address ...')
                    logger.info(f'wallet address is {s_purse}')
                    ele_input.input(s_purse)
                    self.page.wait(2)

                    # CONTINUE
                    s_path = '@@class:v-btn__content@@text():Continue'
                    button = self.page.ele(f'{s_path}', timeout=2)
                    if isinstance(button, NoneElement):
                        logger.info('Step Two: Not Found ...')
                    else:
                        logger.info('Step Two: Continue ...')
                        button.click(by_js=True)
                        self.page.wait(2)

            # Verification Challenge 点击识别验证码
            button = self.page.ele('tag:iframe').ele('.recaptcha-checkbox-border', timeout=2) # noqa
            if isinstance(button, NoneElement):
                logger.info('Step Three: Verification Challenge Not Found ...')
                continue
            else:
                logger.info('Step Three: Verification Challenge ...')
                button.click(by_js=True)
                self.page.wait(1)

            # ele_checkbox = self.page.ele('tag:iframe').ele('.recaptcha-checkbox-checkmark', timeout=2) # noqa
            # print(ele_checkbox.states.is_checked)

            # 验证已经过期，请重新选中该复选框，以便获取新的验证码

            # Recaptcha 要求验证.
            # Recaptcha requires verification.

            # 您已通过验证
            # You are verified

            max_wait_sec = 60
            i = 1
            while i < max_wait_sec:
                s_info = self.page.ele('tag:iframe').ele('.rc-anchor-aria-status', timeout=2).text # noqa
                print(f'{i} {s_info}')
                if s_info.startswith('You are verified') or s_info.startswith('您已通过验证'): # noqa
                    logger.info(f'Recaptcha took {i} seconds. {s_info}')
                    break
                i += 1
                self.page.wait(1)
            # 未通过验证
            if i >= max_wait_sec:
                logger.info(f'Recaptcha failed, took {i} seconds.')
                continue

            # CONTINUE
            s_path = '@@class:v-btn__content@@text():Continue'
            button = self.page.eles(f'{s_path}', timeout=2)
            if isinstance(button, NoneElement):
                logger.info('Continue Button is Not Found ...')
                continue
            else:
                logger.info('Click Continue Button ...')
                button[-1].click(by_js=True)
                self.page.wait(1)

            # This faucet is experiencing high load. If you run into problems funding your wallet, please try \t\t\t\tagain in a few hours.
            # s_info = self.page.ele('.font-weight-bold').text
            # print(s_info)

            i = 1
            while i < max_wait_sec:
                s_info = self.page.ele('.v-alert__content').text
                s_info = s_info.replace('\t', '')
                print(f'Took {i} seconds. {s_info}')
                logger.info(f'Took {i} seconds. {s_info}')
                # Done! Your requested tokens should have arrived at your provided address. You can return here in 24 \t\t\thours to request more.
                if s_info.startswith('Done! Your requested tokens should have arrived'): # noqa
                    logger.info('Success to claim. submit took {i} seconds.')
                    self.update_status(time.time())
                    self.is_update = True
                    self.page.wait(3)
                    return True
                i += 1
                self.page.wait(1)
            # Claim Failed
            if i >= max_wait_sec:
                logger.info(f'Failed to claim, submit took {i} seconds.')
                continue

        return False


def send_msg(instNillionTask, lst_success):
    if len(DEF_DING_TOKEN) > 0 and len(lst_success) > 0:
        s_info = ''
        for s_profile in lst_success:
            if s_profile in instNillionTask.dic_status:
                lst_status = instNillionTask.dic_status[s_profile]
            else:
                lst_status = [s_profile, -1]

            s_info += '- {} {}\n'.format(
                s_profile,
                lst_status[1],
            )
        d_cont = {
            'title': 'Nillion Faucet Claim Finished',
            'text': (
                '- {}\n'
                '{}\n'
                .format(DEF_HEADER_STATUS, s_info)
            )
        }
        ding_msg(d_cont, DEF_DING_TOKEN, msgtype="markdown")


def main(args):
    if args.sleep_sec_at_start > 0:
        logger.info(f'Sleep {args.sleep_sec_at_start} seconds at start !!!') # noqa
        time.sleep(args.sleep_sec_at_start)

    instNillionTask = NillionTask()

    if len(args.profile) > 0:
        items = args.profile.split(',')
    else:
        # 从配置文件里获取钱包名称列表
        instNillionTask.purse_load()
        items = list(instNillionTask.dic_purse.keys())

    profiles = copy.deepcopy(items)

    # 每次随机取一个出来，并从原列表中删除，直到原列表为空
    total = len(profiles)
    n = 0

    lst_success = []

    while profiles:
        n += 1
        logger.info('#'*40)
        s_profile = random.choice(profiles)
        logger.info(f'progress:{n}/{total} [{s_profile}]') # noqa
        profiles.remove(s_profile)

        args.s_profile = s_profile

        def _run():
            instNillionTask.initChrome(args.s_profile)

            for i in [1, 2]:
                s_purse = instNillionTask.dic_purse[instNillionTask.args.s_profile][i] # noqa
                is_claim = instNillionTask.faucet_claim(s_purse)

            instNillionTask.close()
            instNillionTask.status_save()
            return is_claim

        # 出现异常(与页面的连接已断开)，增加重试
        max_try_except = 3
        for j in range(1, max_try_except+1):
            try:
                is_claim = False
                if j > 1:
                    logger.info(f'异常重试，当前是第{j}次执行，最多尝试{max_try_except}次 [{s_profile}]') # noqa

                instNillionTask.set_args(args)
                instNillionTask.status_load()

                if s_profile in instNillionTask.dic_status:
                    lst_status = instNillionTask.dic_status[s_profile]
                else:
                    lst_status = None

                if lst_status:
                    avail_time = lst_status[1]
                    n_sec_wait = time_difference(avail_time) + 24*3600 + 60
                    if n_sec_wait > 0:
                        logger.info(f'[{s_profile}] 还需等待{n_sec_wait}秒')
                        break
                    is_claim = _run()
                else:
                    is_claim = _run()

                if is_claim:
                    instNillionTask.status_save()
                    lst_success.append(s_profile)
                    break
            except Exception as e:
                logger.info(f'[{s_profile}] An error occurred: {str(e)}')
                if j < max_try_except:
                    time.sleep(5)

        if instNillionTask.is_update is False:
            continue

        logger.info(f'[{s_profile}] Finish')

        if len(profiles) > 0:
            sleep_time = random.randint(args.sleep_sec_min, args.sleep_sec_max)
            if sleep_time > 60:
                logger.info('sleep {} minutes ...'.format(int(sleep_time/60)))
            else:
                logger.info('sleep {} seconds ...'.format(int(sleep_time)))
            time.sleep(sleep_time)

    send_msg(instNillionTask, lst_success)


if __name__ == '__main__':
    """
    从钱包列表配置文件中，每次随机取一个出来，并从原列表中删除，直到原列表为空
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--loop_interval', required=False, default=60, type=int,
        help='[默认为 60] 执行完一轮 sleep 的时长(单位是秒)，如果是0，则不循环，只执行一次'
    )
    parser.add_argument(
        '--sleep_sec_min', required=False, default=3, type=int,
        help='[默认为 3] 每个账号执行完 sleep 的最小时长(单位是秒)'
    )
    parser.add_argument(
        '--sleep_sec_max', required=False, default=10, type=int,
        help='[默认为 10] 每个账号执行完 sleep 的最大时长(单位是秒)'
    )
    parser.add_argument(
        '--sleep_sec_at_start', required=False, default=0, type=int,
        help='[默认为 0] 在启动后先 sleep 的时长(单位是秒)'
    )
    parser.add_argument(
        '--profile', required=False, default='',
        help='按指定的 profile 执行，多个用英文逗号分隔'
    )
    args = parser.parse_args()
    if args.loop_interval <= 0:
        main(args)
    else:
        while True:
            main(args)
            logger.info('#####***** Loop sleep {} seconds ...'.format(args.loop_interval)) # noqa
            time.sleep(args.loop_interval)


"""
# noqa
python nillion_faucet.py --profile=p001
python nillion_faucet.py --profile=p010,p011 --sleep_sec_min=600 --sleep_sec_max=1800
"""
