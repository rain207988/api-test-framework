# 08 · pytest 核心与 conftest 装配（api-test-framework · 文档08）

> 一句话：fixture 是框架的"装配车间"——谁依赖谁、什么作用域、什么时候清理，全在这里声明。

## 1. 在整个框架中的位置

```mermaid
flowchart TD
    subgraph conftest.py（session 级装配）
        A["_reset_mall_data (autouse)<br>套件开始重置数据"]
        B["token_manager<br>TokenManager + 注入 login_func"]
        C["rest_client<br>主客户端：token+钩子"]
        D["fresh_client<br>干净客户端"]
        E["chain_client<br>链路专用客户端"]
    end
    A --> C
    B --> C & E
    C & D & E --> F["test_*.py 用例<br>函数签名里要谁就注入谁"]
```

## 2. 涉及文件

| 文件 | 职责 |
|---|---|
| `testcases/conftest.py` | 全部 fixture + pytest_sessionfinish 钩子 |
| `testcases/test_*.py` | 用例：函数签名声明依赖，pytest 自动注入 |

## 3. 如何实现

### 3.1 fixture 四件套速查

| 机制 | 本框架的用法 |
|---|---|
| **定义** `@pytest.fixture` | 7 个 fixture，全部 session 级（客户端/登录/数据重置都是全套件一份） |
| **作用域** `scope="session"` | RestClient、TokenManager、数据重置——创建昂贵且可共享的对象用大作用域 |
| **yield 前后=setup/teardown** | 本框架客户端无需清理（无状态），演示版没写 yield；UI 框架的 driver fixture 有 yield+quit（对照学习） |
| **autouse** | `_reset_mall_data`：所有用例隐式依赖，保证"不重置不跑用例" |

### 3.2 依赖注入的链条

```python
@pytest.fixture(scope="session")
def token_manager() -> TokenManager:
    return TokenManager(login_func=_make_login_func())   # ← 依赖倒置的注入点

@pytest.fixture(scope="session")
def rest_client(token_manager) -> RestClient:            # ← fixture 之间也能互相注入
    ...
```

用例里只需要写：

```python
def test_xxx(self, case, rest_client, fresh_client):     # 要谁写谁，pytest 自动装配
```

**这就是 fixture 与传统 setUp/setUpClass 的本质区别**：依赖关系是"声明式"的图，
不是"继承式"的链；conftest.py 所在同目录的测试自动共享，跨文件零 import。

### 3.3 _reset_mall_data：自动化可重复的基石

```python
@pytest.fixture(scope="session", autouse=True)
def _reset_mall_data():
    resp = TestSupportApi(RestClient(cfg.base_url, cfg.timeout)).reset_data()
    if resp.status_code != 200 or resp.json().get("code") != 0:
        raise RuntimeError("数据重置失败...请先启动 demo-mall")
```

两个设计点：

- **失败要"响"**：被测系统没起时，第一个用例就给出生动报错（含启动命令提示），
  而不是 58 条用例连环炸出一堆 ConnectionError；
- **session 级只做一次**：不是每条用例都重置（那样有状态的用例没法写）；
  重置一次 + 用例自身幂等设计（docs/07 坑 4）= 可重复。

### 3.4 pytest_sessionfinish：环境写进报告

```python
def pytest_sessionfinish(session, exitstatus):
    alluredir = session.config.getoption("--alluredir", default=None)
    if not alluredir or not os.path.isdir(alluredir):
        return
    with open(os.path.join(alluredir, "environment.properties"), "w") as f:
        f.write(f"base_url={cfg.base_url}\nenv={cfg.env}\npython={...}\n")
```

Allure 报告首页的 Environment 面板数据就来自这个文件——报告自证"当时测的是哪个环境"。

## 4. 为什么这样设计

| 决策 | 备选方案 | 结论 |
|---|---|---|
| 客户端全部 session 级 | function 级每用户新建 | HTTP 客户端无用例间状态冲突，复用连接池快；若对象有状态（如浏览器）则必须 function 级 |
| autouse 重置数据 | 用例自己清理自己 | "每个用例自己打扫"在实践中必然漏（失败路径的清理最难写）；起点重置一次 + 幂等用例更可靠 |
| RuntimeError 带修复提示 | 让 ConnectionError 自然抛 | 新手第一天的"被测系统没起"要一秒看懂，这值得单独 10 行代码 |
| fixture 放 conftest | 放 util 模块手动 import | conftest 是 pytest 的官方共享机制，免 import、免命名冲突 |

## 5. 怎么运行/验证

```bash
cd D:\软件测试\api-test-framework

# 看 fixture 装配顺序与注入过程
python -m pytest testcases/test_login.py --setup-show -v 2>&1 | grep -E "SETUP|TEARDOWN" | head -8
# 预期:
#     SETUP    S _reset_mall_data (session 级先跑)
#     SETUP    S token_manager
#     SETUP    S rest_client
#     SETUP    F test_login_api（用例拿到注入）

# 验证 autouse：即使单跑一条用例，数据也被重置
python -m pytest "testcases/test_login.py::TestLoginApi" -k "正确账号" 2>&1 | tail -1
```

## 6. 常见坑

1. **fixture 忘了 return**（function 级）→ 用例拿到 None，报错离根源十万八千里。
2. **作用域错配**：把"每次要不同数据"的对象做成 session 级（比如链路的 order_id）——作用域跟着"对象能否共享"走，不跟"用例多少"走。
3. **conftest 藏太深**：conftest 只对同目录及子目录生效；放 testcases/ 下没问题，放错层级会导致 fixture 找不到。
4. **autouse 里做耗时操作**：autouse 是"所有用例都要付的税"，重置数据 50ms 可以；如果是 5 分钟的东西要想清楚。
5. **pytest.ini 的 addopts 里写死 --alluredir**：本地跑子集时也会全量重建 Allure 结果——可接受（报告是全量视角），但要知道自己配了什么。

## 7. 面试怎么讲

**30 秒版**：
"框架的装配全在 conftest：session 级 autouse fixture 在开跑前把被测系统数据重置成种子状态；
TokenManager 拿到注入的登录函数负责 token 缓存；三个 RestClient fixture 分工——
主客户端带 token 和 401 钩子、干净客户端测未登录、链路客户端和主会话隔离。
用例函数签名里声明要谁，pytest 自动注入。失败快速失败：被测系统没起，
第一个 fixture 就报'请先启动 demo-mall'，而不是 58 条用例连环超时。"

**高频追问**：
1. *"fixture 和 setup/teardown 区别？"* —— 见 docs/05 追问 4；核心是声明式依赖图 vs 继承链。
2. *"为什么数据重置是 session 不是 function？"* —— 频率与状态的权衡：重置是给"套件"一个确定的起点；function 级重置会让有状态链路无法成立，且慢。
3. *"怎么控制某条用例跳过？"* —— `@pytest.mark.skip(reason)`/`skipif`；本框架没有 skip 的用例——简历项目里 skip 是遮羞布，要么修要么删。

## 8. 复现任务清单

- [ ] 1. 写 _reset_mall_data（autouse + 失败带提示）
- [ ] 2. 写 _make_login_func + token_manager fixture
- [ ] 3. 装配三个客户端 fixture（对照 docs/05 的分工表）
- [ ] 4. 用 --setup-show 观察 fixture 执行顺序
- [ ] 5. 实验：把 rest_client 改成 function 级，数日志里的登录次数，体会作用域的意义
- [ ] 6. 实现 pytest_sessionfinish 写 environment.properties，Allure 报告里确认显示
