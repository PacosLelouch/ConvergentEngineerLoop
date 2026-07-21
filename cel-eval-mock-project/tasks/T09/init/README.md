# cel-eval-mock-project

## 安装

```bash
pip install .
```

## 运行测试

```bash
pytest
```

## 使用

```bash
python -m src.cli list --output-dir result.json
python -m src.cli export --output-dir data.csv
python -m src.cli stats --output-dir stats.json
```

> T09 缺陷：安装命令过时（应为 pip install -e .）、--output-dir 已改名为 --out。
