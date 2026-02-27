// static/js/script.js
document.addEventListener('DOMContentLoaded', function() {
    // ========== 全局变量 ==========
    // 定义页存储的函数字典，格式：{ 函数名: [名称, 表达式, 定义域, 自变量] }
    let functions = {};

    // 方程组存储，格式：{ "等式字符串": [左表达式, 右表达式] }
    let equations = {};

    // 不等式组存储，格式：{ "不等式字符串": [左表达式, 右表达式, 关系符] }
    let inequalities = {};

    // ========== 工具函数 ==========
    // 获取当前函数字典，用于API请求
    function getFs() {
        return functions;
    }

    // 重新渲染 MathJax
    function renderMath() {
        if (window.MathJax) {
            MathJax.Hub.Queue(['Typeset', MathJax.Hub]);
        }
    }

    // ========== 标签页切换 ==========
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const tabId = this.dataset.tab;
            tabButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            tabContents.forEach(c => c.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            renderMath();
        });
    });

    // ========== 定义页 ==========
    // 定义页元素
    const funcList = document.getElementById('function-list');
    const funcName = document.getElementById('func-name');
    const funcExpr = document.getElementById('func-expr');
    const funcDomain = document.getElementById('func-domain');
    const funcVar = document.getElementById('func-var');
    const attrSelect = document.getElementById('func-attr-select');
    const attrStr = document.getElementById('func-attr-str');
    const attrView = document.getElementById('func-attr-view');
    const evalVal = document.getElementById('func-eval-val');
    const evalStr = document.getElementById('func-eval-str');
    const evalView = document.getElementById('func-eval-view');
    const saveBtn = document.getElementById('func-save');
    const deleteBtn = document.getElementById('func-delete');
    const evalBtn = document.getElementById('func-eval-btn');

    // 刷新左侧函数列表
    function refreshFunctionList() {
        funcList.innerHTML = '';
        for (let key in functions) {
            let li = document.createElement('li');
            li.textContent = `${key}(${functions[key][3]})`;  // 显示 f(x)
            li.dataset.name = key;
            li.addEventListener('click', function() {
                document.querySelectorAll('#function-list li').forEach(li => li.classList.remove('selected'));
                this.classList.add('selected');
                let f = functions[this.dataset.name];
                funcName.value = f[0];
                funcExpr.value = f[1];
                funcDomain.value = f[2];
                funcVar.value = f[3];
                attrSelect.value = '0';
                updateFunctionAttr(0);
                updateFunctionEval();
            });
            funcList.appendChild(li);
        }
    }

    // 更新函数属性显示
    function updateFunctionAttr(attrIndex) {
        let expr = funcExpr.value;
        let var_ = funcVar.value;
        let domain = funcDomain.value;
        if (!expr) return;

        fetch('/api/function', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'get_attr',
                expr: expr,
                var: var_,
                domain: domain,
                attr_index: attrIndex,
                fs: getFs()
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                attrView.innerHTML = `\\(${data.latex}\\)`;
                attrStr.value = data.str;
                renderMath();
            } else {
                attrView.innerHTML = '';
                attrStr.value = '错误：' + data.error;
            }
        })
        .catch(err => {
            attrView.innerHTML = '';
            attrStr.value = '请求失败';
        });
    }

    // 更新函数求值显示
    function updateFunctionEval() {
        let expr = funcExpr.value;
        let var_ = funcVar.value;
        let val = evalVal.value;
        if (!expr || !val) return;

        fetch('/api/function', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'evaluate',
                expr: expr,
                var: var_,
                val: val,
                fs: getFs()
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                evalView.innerHTML = `\\(${data.latex}\\)`;
                evalStr.value = data.str;
                renderMath();
            } else {
                evalView.innerHTML = '';
                evalStr.value = '错误：' + data.error;
            }
        })
        .catch(err => {
            evalView.innerHTML = '';
            evalStr.value = '请求失败';
        });
    }

    // 保存函数
    saveBtn.addEventListener('click', function() {
        let name = funcName.value.trim();
        if (!name) {
            alert('函数名称不能为空');
            return;
        }
        functions[name] = [name, funcExpr.value, funcDomain.value, funcVar.value];
        refreshFunctionList();
        // 选中刚保存的项
        let items = document.querySelectorAll('#function-list li');
        for (let li of items) {
            if (li.dataset.name === name) {
                li.classList.add('selected');
                break;
            }
        }
        attrSelect.value = '0';
        updateFunctionAttr(0);
        updateFunctionEval();
    });

    // 删除函数
    deleteBtn.addEventListener('click', function() {
        let name = funcName.value.trim();
        if (!name || !functions[name]) return;
        delete functions[name];
        refreshFunctionList();
        // 清空编辑区
        funcName.value = 'f';
        funcExpr.value = 'x**2';
        funcDomain.value = 'Reals';
        funcVar.value = 'x';
        attrView.innerHTML = '';
        attrStr.value = '';
        evalView.innerHTML = '';
        evalStr.value = '';
    });

    // 属性选择变化
    attrSelect.addEventListener('change', function() {
        let idx = parseInt(this.value, 10);
        updateFunctionAttr(idx);
    });

    // 求值按钮
    evalBtn.addEventListener('click', function() {
        updateFunctionEval();
    });

    // 编辑区变化时自动更新属性（保持当前选择）
    funcExpr.addEventListener('input', function() {
        let idx = parseInt(attrSelect.value, 10);
        updateFunctionAttr(idx);
    });
    funcDomain.addEventListener('input', function() {
        let idx = parseInt(attrSelect.value, 10);
        updateFunctionAttr(idx);
    });
    funcVar.addEventListener('input', function() {
        let idx = parseInt(attrSelect.value, 10);
        updateFunctionAttr(idx);
    });
    evalVal.addEventListener('input', function() {
        updateFunctionEval();
    });

    // 初始化一个默认函数
    functions['f'] = ['f', 'x**2', 'Reals', 'x'];
    refreshFunctionList();
    // 选中第一个
    let firstLi = document.querySelector('#function-list li');
    if (firstLi) firstLi.click();

    // ========== 求导页 ==========
    const derivExpr = document.getElementById('derivative-expr');
    const derivVar = document.getElementById('derivative-var');
    const derivOrder = document.getElementById('derivative-order');
    const derivImplicit = document.getElementById('derivative-implicit');
    const derivYVar = document.getElementById('derivative-yvar');
    const derivSpecific = document.getElementById('derivative-specific');
    const derivXVal = document.getElementById('derivative-xval');
    const derivBtn = document.getElementById('derivative-btn');
    const derivOriginal = document.getElementById('derivative-original');
    const derivResult = document.getElementById('derivative-result');
    const derivValue = document.getElementById('derivative-value');

    derivImplicit.addEventListener('change', function() {
        derivYVar.disabled = !this.checked;
        if (!this.checked) derivSpecific.checked = false;
    });
    derivSpecific.addEventListener('change', function() {
        derivXVal.disabled = !this.checked;
    });

    // 实时显示原函数
    derivExpr.addEventListener('input', function() {
        let expr = this.value;
        if (!expr) return;
        fetch('/api/derivative', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ expr: expr, var: 'x', order: '1', fs: getFs() })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                derivOriginal.innerHTML = `\\(f(x)=${data.original}\\)`;
                renderMath();
            }
        })
        .catch(() => {});
    });

    derivBtn.addEventListener('click', function() {
        let expr = derivExpr.value;
        let var_ = derivVar.value;
        let order = derivOrder.value;
        let isImplicit = derivImplicit.checked;
        let yVar = derivYVar.value || 'y';
        let isSpecific = derivSpecific.checked;
        let xVal = derivXVal.value;

        fetch('/api/derivative', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                expr: expr,
                var: var_,
                order: order,
                is_implicit: isImplicit,
                y_var: yVar,
                is_specific: isSpecific,
                x_val: isSpecific ? xVal : null,
                fs: getFs()
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                derivOriginal.innerHTML = `\\(f(x)=${data.original}\\)`;
                derivResult.innerHTML = `\\(f'(x)=${data.derivative}\\)`;
                if (data.derivative_value) {
                    derivValue.innerHTML = `\\(f'(${xVal})=${data.derivative_value}\\)`;
                } else {
                    derivValue.innerHTML = '';
                }
                renderMath();
            } else {
                alert('求导失败：' + data.error);
            }
        })
        .catch(err => alert('网络错误：' + err));
    });
    if (derivExpr.value) derivExpr.dispatchEvent(new Event('input'));

    // ========== 积分页 ==========
    const integralExpr = document.getElementById('integral-expr');
    const integralVar = document.getElementById('integral-var');
    const integralDefinite = document.getElementById('integral-definite');
    const integralLower = document.getElementById('integral-lower');
    const integralUpper = document.getElementById('integral-upper');
    const integralBtn = document.getElementById('integral-btn');
    const integralOriginal = document.getElementById('integral-original');
    const integralAntiderivative = document.getElementById('integral-antiderivative');
    const integralDefiniteValue = document.getElementById('integral-definite-value');

    integralDefinite.addEventListener('change', function() {
        integralLower.disabled = !this.checked;
        integralUpper.disabled = !this.checked;
    });

    integralExpr.addEventListener('input', function() {
        let expr = this.value;
        if (!expr) return;
        fetch('/api/integral', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ expr: expr, var: 'x', fs: getFs() })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                integralOriginal.innerHTML = `\\(f(x)=${data.original}\\)`;
                renderMath();
            }
        })
        .catch(() => {});
    });

    integralBtn.addEventListener('click', function() {
        let expr = integralExpr.value;
        let var_ = integralVar.value;
        let isDefinite = integralDefinite.checked;
        let lower = integralLower.value;
        let upper = integralUpper.value;

        fetch('/api/integral', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                expr: expr,
                var: var_,
                is_definite: isDefinite,
                lower: isDefinite ? lower : null,
                upper: isDefinite ? upper : null,
                fs: getFs()
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                integralOriginal.innerHTML = `\\(f(x)=${data.original}\\)`;
                integralAntiderivative.innerHTML = `\\(F(x)=${data.antiderivative}\\)`;
                if (data.definite_value) {
                    integralDefiniteValue.innerHTML = `\\(\\int_{${lower}}^{${upper}} f(x)dx = ${data.definite_value}\\)`;
                } else {
                    integralDefiniteValue.innerHTML = '';
                }
                renderMath();
            } else {
                alert('积分失败：' + data.error);
            }
        })
        .catch(err => alert('网络错误：' + err));
    });
    if (integralExpr.value) integralExpr.dispatchEvent(new Event('input'));

    // ========== 变形页 ==========
    const simplifyExpr = document.getElementById('simplify-expr');
    const simplifyMethod = document.getElementById('simplify-method');
    const simplifyZhuyuan = document.getElementById('simplify-zhuyuan');
    const simplifyHuanyuan = document.getElementById('simplify-huanyuan');
    const simplifyHuanyuanshi = document.getElementById('simplify-huanyuanshi');
    const simplifyBtn = document.getElementById('simplify-btn');
    const simplifyOriginal = document.getElementById('simplify-original');
    const simplifyResult = document.getElementById('simplify-result');
    const simplifyResultText = document.getElementById('simplify-result-text');

    function updateSimplifyOptions() {
        let idx = parseInt(simplifyMethod.value, 10);
        if (idx === 3) {
            simplifyZhuyuan.disabled = false;
            simplifyHuanyuan.disabled = true;
            simplifyHuanyuanshi.disabled = true;
        } else if (idx === 12) {
            simplifyZhuyuan.disabled = false;
            simplifyHuanyuan.disabled = false;
            simplifyHuanyuanshi.disabled = false;
        } else {
            simplifyZhuyuan.disabled = true;
            simplifyHuanyuan.disabled = true;
            simplifyHuanyuanshi.disabled = true;
        }
    }
    simplifyMethod.addEventListener('change', updateSimplifyOptions);
    updateSimplifyOptions();

    simplifyExpr.addEventListener('input', function() {
        let expr = this.value;
        if (!expr) return;
        fetch('/api/simplify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ expr: expr, method_index: 0, fs: getFs() })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                simplifyOriginal.innerHTML = `\\(${data.original}\\)`;
                renderMath();
            }
        })
        .catch(() => {});
    });

    simplifyBtn.addEventListener('click', function() {
        let expr = simplifyExpr.value;
        let methodIndex = parseInt(simplifyMethod.value, 10);
        let zhuyuan = simplifyZhuyuan.disabled ? null : simplifyZhuyuan.value;
        let huanyuan = simplifyHuanyuan.disabled ? null : simplifyHuanyuan.value;
        let huanyuanshi = simplifyHuanyuanshi.disabled ? null : simplifyHuanyuanshi.value;

        fetch('/api/simplify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                expr: expr,
                method_index: methodIndex,
                zhuyuan: zhuyuan,
                huanyuan: huanyuan,
                huanyuanshi: huanyuanshi,
                fs: getFs()
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                simplifyOriginal.innerHTML = `\\(${data.original}\\)`;
                simplifyResult.innerHTML = `\\(${data.simplified}\\)`;
                simplifyResultText.value = data.simplified_str;
                renderMath();
            } else {
                alert('变形失败：' + data.error);
            }
        })
        .catch(err => alert('网络错误：' + err));
    });
    if (simplifyExpr.value) simplifyExpr.dispatchEvent(new Event('input'));

    // ========== 方程页（含微分方程）==========
    const eqLhs = document.getElementById('equation-lhs');
    const eqRhs = document.getElementById('equation-rhs');
    const eqVar = document.getElementById('equation-var');
    const eqDomain = document.getElementById('equation-domain');
    const eqOde = document.getElementById('equation-ode');
    const eqBtn = document.getElementById('equation-btn');
    const eqOriginal = document.getElementById('equation-original');
    const eqSolution = document.getElementById('equation-solution');
    const eqSolutionText = document.getElementById('equation-solution-text');

    eqOde.addEventListener('change', function() {
        eqVar.disabled = this.checked;
        eqDomain.disabled = this.checked;
        if (this.checked) {
            eqVar.value = 'f(x)';
            eqDomain.value = '';
        } else {
            eqVar.value = 'x';
            eqDomain.value = 'Reals';
        }
        // 触发更新原方程显示
        updateEquationOriginal();
    });

    function updateEquationOriginal() {
        let lhs = eqLhs.value;
        let rhs = eqRhs.value;
        let var_ = eqVar.value;
        let domain = eqDomain.value;
        let isOde = eqOde.checked;
        if (!lhs) return;
        fetch('/api/equation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lhs: lhs,
                rhs: rhs,
                var: var_,
                domain: domain,
                is_ode: isOde,
                fs: getFs()
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                eqOriginal.innerHTML = `\\(${data.original}\\)`;
                renderMath();
            }
        })
        .catch(() => {});
    }

    eqLhs.addEventListener('input', updateEquationOriginal);
    eqRhs.addEventListener('input', updateEquationOriginal);
    eqVar.addEventListener('input', updateEquationOriginal);
    eqDomain.addEventListener('input', updateEquationOriginal);

    eqBtn.addEventListener('click', function() {
        let lhs = eqLhs.value;
        let rhs = eqRhs.value;
        let var_ = eqVar.value;
        let domain = eqDomain.value;
        let isOde = eqOde.checked;

        fetch('/api/equation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lhs: lhs,
                rhs: rhs,
                var: var_,
                domain: domain,
                is_ode: isOde,
                fs: getFs()
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                eqOriginal.innerHTML = `\\(${data.original}\\)`;
                eqSolution.innerHTML = `\\(${data.solution}\\)`;
                eqSolutionText.value = data.solution_str;
                renderMath();
            } else {
                alert('方程求解失败：' + data.error);
            }
        })
        .catch(err => alert('网络错误：' + err));
    });
    if (eqLhs.value) updateEquationOriginal();

    // ========== 方程组页 ==========
    const eqList = document.getElementById('equation-list');
    const eqLhsInput = document.getElementById('eq-lhs');
    const eqRhsInput = document.getElementById('eq-rhs');
    const eqSave = document.getElementById('eq-save');
    const eqDelete = document.getElementById('eq-delete');
    const eqVarsInput = document.getElementById('eq-vars');
    const eqSolve = document.getElementById('eq-solve');
    const eqSystemOriginal = document.getElementById('eqsystem-original');
    const eqSystemSolution = document.getElementById('eqsystem-solution');
    const eqSystemSolutionText = document.getElementById('eqsystem-solution-text');

    function refreshEquationList() {
        eqList.innerHTML = '';
        for (let key in equations) {
            let li = document.createElement('li');
            li.textContent = key;
            li.dataset.key = key;
            li.addEventListener('click', function() {
    document.querySelectorAll('#equation-list li').forEach(li => li.classList.remove('selected'));
    this.classList.add('selected');
    let eq = equations[this.dataset.key];
    eqLhsInput.value = eq[0];
    eqRhsInput.value = eq[1];

    // 分别获取左右表达式的 LaTeX
    Promise.all([
        fetch('/api/latex', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ expr: eq[0], fs: getFs() })
        }).then(res => res.json()),
        fetch('/api/latex', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ expr: eq[1], fs: getFs() })
        }).then(res => res.json())
    ]).then(([lhsRes, rhsRes]) => {
        if (lhsRes.success && rhsRes.success) {
            eqSystemOriginal.innerHTML = `\\(${lhsRes.latex} = ${rhsRes.latex}\\)`;
            renderMath();
        } else {
            eqSystemOriginal.innerHTML = `\\(${eq[0]} = ${eq[1]}\\)`; // 降级显示
        }
    }).catch(() => {
        eqSystemOriginal.innerHTML = `\\(${eq[0]} = ${eq[1]}\\)`;
    });
});
            eqList.appendChild(li);
        }
    }

    eqSave.addEventListener('click', function() {
    let lhs = eqLhsInput.value.trim();
    let rhs = eqRhsInput.value.trim();
    if (!lhs) return;
    let key = lhs + ' = ' + rhs;
    if (!equations[key]) {
        equations[key] = [lhs, rhs];
        refreshEquationList();
    } else {
        // 已存在，可能更新表达式
        equations[key] = [lhs, rhs];
        refreshEquationList();
    }
    // 选中新保存的项
    let items = document.querySelectorAll('#equation-list li');
    for (let li of items) {
        if (li.dataset.key === key) {
            li.classList.add('selected');
            // 手动触发点击事件来更新原式
            li.click();
            break;
        }
    }
});

    eqDelete.addEventListener('click', function() {
        let selected = document.querySelector('#equation-list li.selected');
        if (!selected) return;
        let key = selected.dataset.key;
        delete equations[key];
        refreshEquationList();
        eqSystemOriginal.innerHTML = '';
        eqSystemSolution.innerHTML = '';
        eqSystemSolutionText.value = '';
    });

    eqSolve.addEventListener('click', function() {
        let eqsArray = Object.values(equations);
        let vars = eqVarsInput.value;
        fetch('/api/equationsystem', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                equations: eqsArray,
                variables: vars,
                fs: getFs()
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                eqSystemSolution.innerHTML = `\\(${data.solution}\\)`;
                eqSystemSolutionText.value = data.solution;
                renderMath();
            } else {
                alert('求解失败：' + data.error);
            }
        })
        .catch(err => alert('网络错误：' + err));
    });

    // 默认添加一个示例方程
    equations['x + y = 0'] = ['x + y', '0'];
    refreshEquationList();
    if (eqList.firstChild) eqList.firstChild.click();

    // ========== 不等式页 ==========
    const ineqLhs = document.getElementById('inequality-lhs');
    const ineqRhs = document.getElementById('inequality-rhs');
    const ineqRel = document.getElementById('inequality-rel');
    const ineqVar = document.getElementById('inequality-var');
    const ineqDomain = document.getElementById('inequality-domain');
    const ineqBtn = document.getElementById('inequality-btn');
    const ineqOriginal = document.getElementById('inequality-original');
    const ineqSolution = document.getElementById('inequality-solution');
    const ineqSolutionText = document.getElementById('inequality-solution-text');

    function updateInequalityOriginal() {
        let lhs = ineqLhs.value;
        let rhs = ineqRhs.value;
        let rel = ineqRel.value;
        let var_ = ineqVar.value;
        let domain = ineqDomain.value;
        if (!lhs) return;
        fetch('/api/inequality', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lhs: lhs,
                rhs: rhs,
                rel: rel,
                var: var_,
                domain: domain,
                fs: getFs()
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                ineqOriginal.innerHTML = `\\(${data.original}\\)`;
                renderMath();
            }
        })
        .catch(() => {});
    }

    ineqLhs.addEventListener('input', updateInequalityOriginal);
    ineqRhs.addEventListener('input', updateInequalityOriginal);
    ineqRel.addEventListener('change', updateInequalityOriginal);
    ineqVar.addEventListener('input', updateInequalityOriginal);
    ineqDomain.addEventListener('input', updateInequalityOriginal);

    ineqBtn.addEventListener('click', function() {
        let lhs = ineqLhs.value;
        let rhs = ineqRhs.value;
        let rel = ineqRel.value;
        let var_ = ineqVar.value;
        let domain = ineqDomain.value;

        fetch('/api/inequality', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lhs: lhs,
                rhs: rhs,
                rel: rel,
                var: var_,
                domain: domain,
                fs: getFs()
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                ineqOriginal.innerHTML = `\\(${data.original}\\)`;
                ineqSolution.innerHTML = `\\(${data.solution}\\)`;
                ineqSolutionText.value = data.solution_str;
                renderMath();
            } else {
                alert('不等式求解失败：' + data.error);
            }
        })
        .catch(err => alert('网络错误：' + err));
    });
    if (ineqLhs.value) updateInequalityOriginal();

    // ========== 不等式组页 ==========
    const ineqList = document.getElementById('inequality-list');
    const ineqLhsInput = document.getElementById('ineq-lhs');
    const ineqRhsInput = document.getElementById('ineq-rhs');
    const ineqRelSelect = document.getElementById('ineq-rel');
    const ineqSave = document.getElementById('ineq-save');
    const ineqDelete = document.getElementById('ineq-delete');
    const ineqVarInput = document.getElementById('ineq-var');
    const ineqSolve = document.getElementById('ineq-solve');
    const ineqSystemOriginal = document.getElementById('ineqsystem-original');
    const ineqSystemSolution = document.getElementById('ineqsystem-solution');
    const ineqSystemSolutionText = document.getElementById('ineqsystem-solution-text');

    function refreshInequalityList() {
        ineqList.innerHTML = '';
        for (let key in inequalities) {
            let li = document.createElement('li');
            li.textContent = key;
            li.dataset.key = key;
            li.addEventListener('click', function() {
    document.querySelectorAll('#inequality-list li').forEach(li => li.classList.remove('selected'));
    this.classList.add('selected');
    let ineq = inequalities[this.dataset.key];
    ineqLhsInput.value = ineq[0];
    ineqRhsInput.value = ineq[1];
    ineqRelSelect.value = ineq[2];

    // 分别获取左右表达式的 LaTeX
    Promise.all([
        fetch('/api/latex', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ expr: ineq[0], fs: getFs() })
        }).then(res => res.json()),
        fetch('/api/latex', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ expr: ineq[1], fs: getFs() })
        }).then(res => res.json())
    ]).then(([lhsRes, rhsRes]) => {
        if (lhsRes.success && rhsRes.success) {
            ineqSystemOriginal.innerHTML = `\\(${lhsRes.latex} ${ineq[2]} ${rhsRes.latex}\\)`;
            renderMath();
        } else {
            ineqSystemOriginal.innerHTML = `\\(${ineq[0]} ${ineq[2]} ${ineq[1]}\\)`;
        }
    }).catch(() => {
        ineqSystemOriginal.innerHTML = `\\(${ineq[0]} ${ineq[2]} ${ineq[1]}\\)`;
    });
});
            ineqList.appendChild(li);
        }
    }

    ineqSave.addEventListener('click', function() {
    let lhs = ineqLhsInput.value.trim();
    let rhs = ineqRhsInput.value.trim();
    let rel = ineqRelSelect.value;
    if (!lhs) return;
    let key = lhs + ' ' + rel + ' ' + rhs;
    if (!inequalities[key]) {
        inequalities[key] = [lhs, rhs, rel];
        refreshInequalityList();
    } else {
        inequalities[key] = [lhs, rhs, rel];
        refreshInequalityList();
    }
    let items = document.querySelectorAll('#inequality-list li');
    for (let li of items) {
        if (li.dataset.key === key) {
            li.classList.add('selected');
            li.click();
            break;
        }
    }
});

    ineqDelete.addEventListener('click', function() {
        let selected = document.querySelector('#inequality-list li.selected');
        if (!selected) return;
        let key = selected.dataset.key;
        delete inequalities[key];
        refreshInequalityList();
        ineqSystemOriginal.innerHTML = '';
        ineqSystemSolution.innerHTML = '';
        ineqSystemSolutionText.value = '';
    });

    ineqSolve.addEventListener('click', function() {
        let ineqsArray = Object.values(inequalities);
        let var_ = ineqVarInput.value;
        fetch('/api/inequalitysystem', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                inequalities: ineqsArray,
                variable: var_,
                fs: getFs()
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                ineqSystemSolution.innerHTML = `\\(${data.solution}\\)`;
                ineqSystemSolutionText.value = data.solution;
                renderMath();
            } else {
                alert('求解失败：' + data.error);
            }
        })
        .catch(err => alert('网络错误：' + err));
    });

    // 默认添加一个示例不等式
    inequalities['x > 0'] = ['x', '0', '>'];
    refreshInequalityList();
    if (ineqList.firstChild) ineqList.firstChild.click();

    // ========== 帮助页 ==========
    // 无需JS，已内联 iframe
});