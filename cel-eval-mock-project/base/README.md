# cel-eval-mock-project

CEL A/B 评测用 Mock 项目。所有模块功能完整、测试全部通过。

## 安装

```bash
pip install -e .
```

## 运行测试

```bash
pytest
```

## 使用

```bash
python -m src.cli list --out result.json
python -m src.cli export --format csv --out data.csv
python -m src.cli stats --out stats.json
```

`export_csv([])` 对空数据返回空字符串；写入文件时固定使用 UTF-8。
