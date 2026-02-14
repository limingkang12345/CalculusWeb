document.addEventListener('DOMContentLoaded', function() {
    // ---------- 标签页切换 ----------
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const tabId = this.dataset.tab;
            tabButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            tabContents.forEach(c => c.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            if (window.MathJax) MathJax.Hub.Queue(['Typeset', MathJax.Hub]);
        });
    });

    // 公共渲染函数
    function renderMath() {
        if (window.MathJax) MathJax.Hub.Queue(['Typeset', MathJax.Hub]);
    }

    // ---------- 求导页面 ----------
    const implicitCheckbox = document.getElementById('derivative-implicit');
    const specificCheckbox = document.getElementById('derivative-specific');
    const yvarInput = document.getElementById('derivative-yvar');
    const xvalInput = document.getElementById('derivative-xval');

    implicitCheckbox.addEventListener('change', function() {
        yvarInput.disabled = !this.checked;
        if (!this.checked) specificCheckbox.checked = false;
    });
    specificCheckbox.addEventListener('change', function() {
        xvalInput.disabled = !this.checked;
    });

    const derivExprInput = document.getElementById('derivative-expr');
    derivExprInput.addEventListener('input', function() {
        const expr = this.value;
        if (!expr) return;
        fetch('/api/derivative', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ expr: expr, var: 'x', order: '1' })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('derivative-original').innerHTML = `\\(f(x)=${data.original}\\)`;
                renderMath();
            }
        })
        .catch(() => {});
    });

    document.getElementById('derivative-btn').addEventListener('click', function() {
        const expr = derivExprInput.value;
        const var_ = document.getElementById('derivative-var').value;
        const order = document.getElementById('derivative-order').value;
        const isImplicit = implicitCheckbox.checked;
        const yVar = yvarInput.value || 'y';
        const isSpecific = specificCheckbox.checked;
        const xVal = xvalInput.value;

        fetch('/api/derivative', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                expr, var: var_, order, is_implicit: isImplicit, y_var: yVar,
                is_specific: isSpecific, x_val: isSpecific ? xVal : null
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('derivative-original').innerHTML = `\\(f(x)=${data.original}\\)`;
                document.getElementById('derivative-result').innerHTML = `\\(f'(x)=${data.derivative}\\)`;
                const valDiv = document.getElementById('derivative-value');
                if (data.derivative_value) {
                    valDiv.innerHTML = `\\(f'(${xVal})=${data.derivative_value}\\)`;
                } else {
                    valDiv.innerHTML = '';
                }
                renderMath();
            } else {
                alert('求导失败：' + data.error);
            }
        })
        .catch(err => alert('网络错误：' + err));
    });
    if (derivExprInput.value) derivExprInput.dispatchEvent(new Event('input'));

    // ---------- 积分页面 ----------
    const definiteCheckbox = document.getElementById('integral-definite');
    const lowerInput = document.getElementById('integral-lower');
    const upperInput = document.getElementById('integral-upper');

    definiteCheckbox.addEventListener('change', function() {
        lowerInput.disabled = !this.checked;
        upperInput.disabled = !this.checked;
    });

    const integralExprInput = document.getElementById('integral-expr');
    integralExprInput.addEventListener('input', function() {
        const expr = this.value;
        if (!expr) return;
        fetch('/api/integral', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ expr: expr, var: 'x' })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('integral-original').innerHTML = `\\(f(x)=${data.original}\\)`;
                renderMath();
            }
        })
        .catch(() => {});
    });

    document.getElementById('integral-btn').addEventListener('click', function() {
        const expr = integralExprInput.value;
        const var_ = document.getElementById('integral-var').value;
        const isDefinite = definiteCheckbox.checked;
        const lower = lowerInput.value;
        const upper = upperInput.value;

        fetch('/api/integral', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                expr, var: var_, is_definite: isDefinite,
                lower: isDefinite ? lower : null,
                upper: isDefinite ? upper : null
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('integral-original').innerHTML = `\\(f(x)=${data.original}\\)`;
                document.getElementById('integral-antiderivative').innerHTML = `\\(F(x)=${data.antiderivative}\\)`;
                const defDiv = document.getElementById('integral-definite-value');
                if (data.definite_value) {
                    defDiv.innerHTML = `\\(\\int_{${lower}}^{${upper}} f(x)dx = ${data.definite_value}\\)`;
                } else {
                    defDiv.innerHTML = '';
                }
                renderMath();
            } else {
                alert('积分失败：' + data.error);
            }
        })
        .catch(err => alert('网络错误：' + err));
    });
    if (integralExprInput.value) integralExprInput.dispatchEvent(new Event('input'));

    // ---------- 变形页面（新增选项控制）----------
    const simplifyMethod = document.getElementById('simplify-method');
    const zhuyuanInput = document.getElementById('simplify-zhuyuan');
    const huanyuanInput = document.getElementById('simplify-huanyuan');
    const huanyuanshiInput = document.getElementById('simplify-huanyuanshi');

    // 根据变形方法启用/禁用选项输入框（完全模仿原Qt逻辑）
    function updateSimplifyOptions() {
        const idx = parseInt(simplifyMethod.value, 10);
        // 索引3: 主元(collect) -> 启用主元符号
        // 索引12: 换元 -> 启用所有三个
        // 其他: 禁用所有
        if (idx === 3) {
            zhuyuanInput.disabled = false;
            huanyuanInput.disabled = true;
            huanyuanshiInput.disabled = true;
        } else if (idx === 12) {
            zhuyuanInput.disabled = false;
            huanyuanInput.disabled = false;
            huanyuanshiInput.disabled = false;
        } else {
            zhuyuanInput.disabled = true;
            huanyuanInput.disabled = true;
            huanyuanshiInput.disabled = true;
        }
    }
    simplifyMethod.addEventListener('change', updateSimplifyOptions);
    updateSimplifyOptions(); // 初始化

    const simplifyExprInput = document.getElementById('simplify-expr');
    simplifyExprInput.addEventListener('input', function() {
        const expr = this.value;
        if (!expr) return;
        fetch('/api/simplify', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ expr: expr, method_index: 0 })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('simplify-original').innerHTML = `\\(${data.original}\\)`;
                renderMath();
            }
        })
        .catch(() => {});
    });

    document.getElementById('simplify-btn').addEventListener('click', function() {
        const expr = simplifyExprInput.value;
        const methodIndex = parseInt(simplifyMethod.value, 10);
        const zhuyuan = zhuyuanInput.disabled ? null : zhuyuanInput.value;
        const huanyuan = huanyuanInput.disabled ? null : huanyuanInput.value;
        const huanyuanshi = huanyuanshiInput.disabled ? null : huanyuanshiInput.value;

        fetch('/api/simplify', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                expr: expr,
                method_index: methodIndex,
                zhuyuan: zhuyuan,
                huanyuan: huanyuan,
                huanyuanshi: huanyuanshi
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('simplify-original').innerHTML = `\\(${data.original}\\)`;
                document.getElementById('simplify-result').innerHTML = `\\(${data.simplified}\\)`;
                document.getElementById('simplify-result-text').value = data.simplified_str;
                renderMath();
            } else {
                alert('变形失败：' + data.error);
            }
        })
        .catch(err => alert('网络错误：' + err));
    });
    if (simplifyExprInput.value) simplifyExprInput.dispatchEvent(new Event('input'));

    // ---------- 方程页面 ----------
    const eqLhs = document.getElementById('equation-lhs');
    const eqRhs = document.getElementById('equation-rhs');
    const eqVar = document.getElementById('equation-var');
    const eqDomain = document.getElementById('equation-domain');

    function updateEquationOriginal() {
        const lhs = eqLhs.value;
        const rhs = eqRhs.value;
        const var_ = eqVar.value;
        const domain = eqDomain.value;
        if (!lhs) return;
        fetch('/api/equation', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ lhs, rhs, var: var_, domain })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('equation-original').innerHTML = `\\(${data.original}\\)`;
                renderMath();
            }
        })
        .catch(() => {});
    }

    eqLhs.addEventListener('input', updateEquationOriginal);
    eqRhs.addEventListener('input', updateEquationOriginal);
    eqVar.addEventListener('input', updateEquationOriginal);
    eqDomain.addEventListener('input', updateEquationOriginal);

    document.getElementById('equation-btn').addEventListener('click', function() {
        const lhs = eqLhs.value;
        const rhs = eqRhs.value;
        const var_ = eqVar.value;
        const domain = eqDomain.value;

        fetch('/api/equation', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ lhs, rhs, var: var_, domain })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('equation-original').innerHTML = `\\(${data.original}\\)`;
                document.getElementById('equation-solution').innerHTML = `\\(${data.solution}\\)`;
                document.getElementById('equation-solution-text').value = data.solution_str;
                renderMath();
            } else {
                alert('方程求解失败：' + data.error);
            }
        })
        .catch(err => alert('网络错误：' + err));
    });
    if (eqLhs.value) updateEquationOriginal();

    // ---------- 不等式页面 ----------
    const ineqLhs = document.getElementById('inequality-lhs');
    const ineqRhs = document.getElementById('inequality-rhs');
    const ineqRel = document.getElementById('inequality-rel');
    const ineqVar = document.getElementById('inequality-var');
    const ineqDomain = document.getElementById('inequality-domain');

    function updateInequalityOriginal() {
        const lhs = ineqLhs.value;
        const rhs = ineqRhs.value;
        const rel = ineqRel.value;
        const var_ = ineqVar.value;
        const domain = ineqDomain.value;
        if (!lhs) return;
        fetch('/api/inequality', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ lhs, rhs, rel, var: var_, domain })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('inequality-original').innerHTML = `\\(${data.original}\\)`;
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

    document.getElementById('inequality-btn').addEventListener('click', function() {
        const lhs = ineqLhs.value;
        const rhs = ineqRhs.value;
        const rel = ineqRel.value;
        const var_ = ineqVar.value;
        const domain = ineqDomain.value;

        fetch('/api/inequality', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ lhs, rhs, rel, var: var_, domain })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('inequality-original').innerHTML = `\\(${data.original}\\)`;
                document.getElementById('inequality-solution').innerHTML = `\\(${data.solution}\\)`;
                document.getElementById('inequality-solution-text').value = data.solution_str;
                renderMath();
            } else {
                alert('不等式求解失败：' + data.error);
            }
        })
        .catch(err => alert('网络错误：' + err));
    });
    if (ineqLhs.value) updateInequalityOriginal();
});