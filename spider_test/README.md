### Download the spider dataset

- Go to the spider site and click download (from GG Drive)
- This will give you a `spider_data.zip` file
- Unzip it and put it in the `spider_data` folder

### Clone the spider git repo

```bash
git clone https://github.com/taoyds/spider.git
```

### Test the evaluation script

```bash
python spider/evaluation.py \
--gold spider/evaluation_examples/gold_example.txt \
--pred spider/evaluation_examples/gold_example.txt \
--etype exec \
--db spider_data/database \
--table spider_data/tables.json
```

### Prepare the prediction file

Prepare the prediction file which contains your query for each question.
For example, if you choose to test against the dev set

- The questions are in `spider_data/dev.json`
- For each question, place your query in a single line in the prediction file, the line number should be the same as the question number
- The solution key file is `spider_data/dev_gold.sql`
- Run the evaluation script with the following command:

```bash
python spider/evaluation.py \
--gold spider_data/dev_gold.sql \
--pred <your_prediction_file> \
--etype exec \
--db spider_data/database \
--table spider_data/tables.json
```
