import random
import string
import time
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import json


def generate_invite_code() -> str:
    """生成六位邀请码：首位数字0，第二位字母，后四位数字字母交替且不连续"""
    # 模式：数字 + 字母 + 数字 + 字母 + 数字 + 字母
    # 确保不连续相同类型

    chars = ['0']  # 首位固定为0

    # 第二位是大写字母
    chars.append(random.choice(string.ascii_uppercase))

    # 后面四位交替：数字、字母、数字、字母
    for i in range(4):
        if i % 2 == 0:
            # 偶数位置：数字（避免与首位重复）
            chars.append(random.choice(string.digits.replace('0', '')))
        else:
            # 奇数位置：字母
            chars.append(random.choice(string.ascii_uppercase))

    return ''.join(chars)


def load_auth_token() -> str:
    """从auth.txt文件加载认证令牌"""
    try:
        # 尝试多个可能的路径
        possible_paths = ['auth.txt']
        auth_token = ""

        for path in possible_paths:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    auth_token = f.read().strip()
                    break
            except FileNotFoundError:
                continue

        if not auth_token:
            print("错误：找不到auth.txt文件")
            return ""

        # 移除可能存在的Bearer前缀
        if auth_token.startswith('Bearer '):
            auth_token = auth_token[7:].strip()

        # 移除所有空白字符，包括换行符、制表符等
        auth_token = ''.join(auth_token.split())

        if not auth_token:
            print("错误：auth.txt文件为空")
            return ""

        return auth_token

    except UnicodeDecodeError:
        print("错误：auth.txt文件编码不正确，请确保文件为UTF-8编码")
        return ""
    except Exception as e:
        print(f"读取auth.txt时出错: {e}")
        return ""


def load_used_codes(file_path: str = "used_codes.txt") -> set:
    """加载已使用的邀请码集合"""
    if not os.path.exists(file_path):
        return set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}
    except Exception as e:
        print(f"读取已使用邀请码文件时出错: {e}")
        return set()


def load_invalid_codes(file_path: str = "invalid_codes.txt") -> set:
    """加载无效的邀请码集合"""
    if not os.path.exists(file_path):
        return set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}
    except Exception as e:
        print(f"读取无效邀请码文件时出错: {e}")
        return set()


def save_used_code(code: str, file_path: str = "used_codes.txt"):
    """保存已使用的邀请码"""
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"{code}\n")
    except Exception as e:
        print(f"保存邀请码时出错: {e}")


def save_success_code(code: str, file_path: str = "success.txt"):
    """保存成功的邀请码"""
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"{code}\n")
    except Exception as e:
        print(f"保存成功邀请码时出错: {e}")


def save_invalid_code(code: str, file_path: str = "invalid_codes.txt"):
    """保存无效的邀请码"""
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"{code}\n")
    except Exception as e:
        print(f"保存无效邀请码时出错: {e}")


def submit_invite_code(invite_code: str, auth_token: str, session: requests.Session, max_retries: int = 5, retry_delay: float = 2.0) -> tuple[str, bool, str]:
    """提交单个邀请码，一直重试直到成功或达到最大重试次数"""
    url = "https://sora.chatgpt.com/backend/project_y/invite/accept"

    headers = {
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'authorization': f'Bearer {auth_token}',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'oai-device-id': '2444164b-a5fd-4f13-8ed6-f5299213a979',
        'origin': 'https://sora.chatgpt.com',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://sora.chatgpt.com/explore',
        'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        'sec-ch-ua-arch': '"x86"',
        'sec-ch-ua-bitness': '"64"',
        'sec-ch-ua-full-version': '"140.0.7339.208"',
        'sec-ch-ua-full-version-list': '"Chromium";v="140.0.7339.208", "Not=A?Brand";v="24.0.0.0", "Google Chrome";v="140.0.7339.208"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"Windows"',
        'sec-ch-ua-platform-version': '"10.0.0"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
    }

    data = {
        "invite_code": invite_code
    }

    for attempt in range(max_retries):
        try:
            response = session.post(
                url,
                headers=headers,
                data=json.dumps(data),
                timeout=None  # 无超时限制，一直等待响应
            )

            # 检查响应状态
            if response.status_code == 200:
                print(f"[SUCCESS] 邀请码 {invite_code} 提交成功！")
                return ("success", True, invite_code)
            elif response.status_code == 403:
                print(f"[INVALID_CODE] 邀请码 {invite_code} 无效，需要更换")
                return ("invalid_code", False, invite_code)
            elif response.status_code == 429:
                print(f"[RATE_LIMITED] 邀请码 {invite_code} 遇到速率限制，重试中... (尝试 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:  # 如果还有重试次数
                    time.sleep(retry_delay * (attempt + 1))  # 每次重试增加等待时间
                    continue
                else:
                    print(f"[RATE_LIMITED] 邀请码 {invite_code} 重试{max_retries}次后仍遇到速率限制，放弃此邀请码")
                    return ("rate_limited_max", False, invite_code)
            else:
                print(f"[ERROR] 邀请码 {invite_code} 返回状态码: {response.status_code}")
                if attempt < max_retries - 1:  # 如果还有重试次数
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"[ERROR] 邀请码 {invite_code} 重试{max_retries}次后仍失败，放弃此邀请码")
                    return ("error_max", False, invite_code)

        except requests.exceptions.RequestException as e:
            print(f"[REQUEST_ERROR] 邀请码 {invite_code} 请求错误，重试中...: {e}")
            if attempt < max_retries - 1:  # 如果还有重试次数
                time.sleep(retry_delay)
                continue
            else:
                print(f"[REQUEST_ERROR] 邀请码 {invite_code} 重试{max_retries}次后仍失败，放弃此邀请码")
                return ("request_error_max", False, invite_code)

    # 理论上不会到达这里，但为了安全起见
    return ("max_retries_exceeded", False, invite_code)


def worker(invite_code: str, auth_token: str, used_codes: set, lock: threading.Lock, max_retries: int = 5, retry_delay: float = 2.0) -> tuple[str, bool, str]:
    """工作线程：提交邀请码"""
    with lock:
        # 先检查邀请码是否已经被使用
        if invite_code in used_codes:
            return ("duplicate", False, invite_code)

        # 预先将邀请码添加到已使用集合，防止其他线程重复使用
        used_codes.add(invite_code)

    # 为每个线程创建独立的session
    session = requests.Session()

    result, success, code = submit_invite_code(invite_code, auth_token, session, max_retries, retry_delay)

    if success:
        with lock:
            # 成功后保存到文件
            save_used_code(invite_code)
            save_success_code(invite_code)
    else:
        # 如果失败了，从used_codes中移除，允许重试
        with lock:
            used_codes.discard(invite_code)
            if result == "invalid_code":
                # 无效邀请码单独保存，不允许重试
                save_invalid_code(invite_code)

    return (result, success, invite_code)


def submit_invite_codes(
    max_workers: int = 5,
    delay: float = 3.0,  # 增大延迟，避免速率限制
    used_codes_file: str = "used_codes.txt",
    success_file: str = "success.txt",
    invalid_codes_file: str = "invalid_codes.txt",
    max_retries: int = 10,  # 增加最大重试次数
    retry_delay: float = 5.0  # 增大重试延迟
) -> None:
    """无限生成并提交邀请码的主函数，遇到无效邀请码时自动生成新邀请码替换，按Ctrl+C停止"""
    auth_token = load_auth_token()
    if not auth_token:
        print("无法获取认证令牌，请检查auth.txt文件")
        return

    used_codes = load_used_codes(used_codes_file)
    invalid_codes = load_invalid_codes(invalid_codes_file)
    lock = threading.Lock()

    print("开始无限生成并提交邀请码...")
    print(f"线程数: {max_workers}")
    print(f"延时: {delay}秒")
    print(f"最大重试次数: {max_retries}")
    print(f"重试延时: {retry_delay}秒")
    print(f"已使用邀请码数量: {len(used_codes)}")
    print(f"已知无效邀请码数量: {len(invalid_codes)}")
    print("按 Ctrl+C 停止程序")

    start_time = time.time()
    last_success_count = 0

    # 统计结果
    results = {"success": 0, "failed": 0, "duplicate": 0, "invalid_code": 0, "rate_limited": 0, "error": 0, "request_error": 0, "rate_limited_max": 0, "error_max": 0, "request_error_max": 0}
    processed_codes = 0

    try:
        # 使用线程池处理邀请码
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 初始生成一批邀请码
            invite_codes = []
            for _ in range(max_workers * 2):  # 初始生成一些邀请码
                code = generate_invite_code()
                with lock:
                    while code in used_codes or code in invalid_codes:
                        code = generate_invite_code()
                invite_codes.append(code)

            # 提交任务
            future_to_code = {executor.submit(worker, code, auth_token, used_codes, lock, max_retries, retry_delay): code for code in invite_codes}

            while future_to_code:
                for future in as_completed(future_to_code):
                    try:
                        result, success, code = future.result()

                        # 从待处理任务中移除
                        del future_to_code[future]

                        processed_codes += 1
                        results[result] = results.get(result, 0) + 1

                        if success:
                            results["success"] += 1
                            current_success = results["success"]

                            # 每成功10个显示一次进度
                            if current_success % 10 == 0 and current_success != last_success_count:
                                print(f"[PROGRESS] 已成功提交 {current_success} 个邀请码")
                                last_success_count = current_success
                        elif result == "invalid_code":
                            # 邀请码无效，已在worker函数中保存到invalid_codes文件
                            with lock:
                                invalid_codes.add(code)

                            print(f"[INVALID] 邀请码 {code} 无效，已记录")
                            results["invalid_code"] += 1

                            # 生成新的邀请码替换
                            new_code = generate_invite_code()
                            with lock:
                                while new_code in used_codes or new_code in invalid_codes:
                                    new_code = generate_invite_code()

                            print(f"[REPLACE] 用新邀请码 {new_code} 替换无效邀请码 {code}")

                            # 提交新邀请码的任务
                            new_future = executor.submit(worker, new_code, auth_token, used_codes, lock, max_retries, retry_delay)
                            future_to_code[new_future] = new_code
                        elif result in ["rate_limited_max", "error_max", "request_error_max"]:
                            # 这些是达到最大重试次数后放弃的邀请码
                            print(f"[GIVE_UP] 邀请码 {code} 达到最大重试次数，放弃此邀请码")

                            # 从used_codes中移除，因为它实际上没有成功使用
                            with lock:
                                used_codes.discard(code)

                            # 记录到对应的统计中
                            if result == "rate_limited_max":
                                results["rate_limited_max"] += 1
                            elif result == "error_max":
                                results["error_max"] += 1
                            else:  # request_error_max
                                results["request_error_max"] += 1

                            # 生成新的邀请码替换
                            new_code = generate_invite_code()
                            with lock:
                                while new_code in used_codes or new_code in invalid_codes:
                                    new_code = generate_invite_code()

                            print(f"[REPLACE] 用新邀请码 {new_code} 替换放弃的邀请码 {code}")

                            # 提交新邀请码的任务
                            new_future = executor.submit(worker, new_code, auth_token, used_codes, lock, max_retries, retry_delay)
                            future_to_code[new_future] = new_code
                        else:
                            results["failed"] += 1

                        # 添加延时避免请求过于频繁
                        if delay > 0:
                            time.sleep(delay)

                    except Exception as e:
                        print(f"线程执行出错: {e}")
                        results["error"] += 1
                        processed_codes += 1

    except KeyboardInterrupt:
        print("\n\n检测到中断信号，正在停止...")

    end_time = time.time()

    print("\n====== 程序停止 ======")
    print(f"总运行时间: {end_time - start_time:.2f}秒")
    print(f"成功: {results['success']} 个")
    print(f"失败: {results['failed']} 个")
    print(f"重复: {results['duplicate']} 个")
    print(f"无效邀请码: {results['invalid_code']} 个")
    print(f"限流: {results['rate_limited']} 个")
    print(f"错误: {results['error']} 个")
    print(f"请求错误: {results['request_error']} 个")
    print(f"限流放弃: {results['rate_limited_max']} 个")
    print(f"错误放弃: {results['error_max']} 个")
    print(f"请求错误放弃: {results['request_error_max']} 个")
    print(f"总处理邀请码数: {processed_codes} 个")
    print(f"成功邀请码已保存到: {success_file}")
    print(f"使用过的邀请码已保存到: {used_codes_file}")
    print(f"无效邀请码已保存到: {invalid_codes_file}")


def test_invite_code_format():
    """测试邀请码生成格式"""
    print("生成10个邀请码测试格式：")
    for i in range(10):
        code = generate_invite_code()
        print(f"{i+1:2d}: {code}")

        # 验证格式
        assert len(code) == 6, f"长度错误：{len(code)}"
        assert code[0] == '0', f"首位错误：{code[0]}"
        assert code[1].isalpha() and code[1].isupper(), f"第二位错误：{code[1]}"

        # 检查后面四位是否交替
        for j in range(2, 6):
            if j % 2 == 0:  # 偶数位置应该是数字
                assert code[j].isdigit(), f"位置{j+1}应该是数字：{code[j]}"
            else:  # 奇数位置应该是字母
                assert code[j].isalpha() and code[j].isupper(), f"位置{j+1}应该是字母：{code[j]}"

        print("    ✓ 格式正确")


if __name__ == "__main__":
    # 测试邀请码格式
    test_invite_code_format()

    print("\n" + "="*50)
    print("邀请码格式测试完成，开始无限运行...")
    print("="*50 + "\n")

    # 无限运行配置 - 增大延迟避免速率限制，提高重试次数确保无限运行
    submit_invite_codes(
        max_workers=3,      # 并发线程数
        delay=3.0,          # 每个请求间的延时（秒）- 增大以避免速率限制
        used_codes_file="used_codes.txt",  # 已使用邀请码保存文件
        success_file="success.txt",  # 成功邀请码保存文件
        invalid_codes_file="invalid_codes.txt",  # 无效邀请码保存文件
        max_retries=20,     # 最大重试次数 - 大幅增加确保无限重试
        retry_delay=8.0     # 重试延时（秒）- 增大延迟
    )