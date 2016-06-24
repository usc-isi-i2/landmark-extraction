site=$1

data_dir=/Users/amandeep/Github/uk-hack/data/weapons

rm "$data_dir"/$site/rules.json
cd /Users/amandeep/Github/memex/memexpython/
. venv/bin/activate
cd src/
python -m learning.RuleLearnerAllSlots "$data_dir"/$site/train/ > "$data_dir"/$site/rules.json 
cd ..
. venv/bin/deactivate
cd /Users/amandeep/Github/landmark-extraction/src 

rm -r /tmp/ukhack/output/; spark-submit --master local[*]    --executor-memory=8g     --driver-memory=8g    --py-files lib/python-lib.zip    landmark_extractor_cdr2.py "$data_dir"/$site/test/  /tmp/ukhack/output "$data_dir"/$site/rules.json

echo "done"

cd /tmp/ukhack/output/
test_jl="$site"_extractions_test.jl

mv part-00000  $test_jl
cd "$data_dir"/$site/
rm -rf extractions
mkdir extractions
mv /tmp/ukhack/output/$test_jl  "$data_dir"/$site/extractions/


cd /Users/amandeep/Github/landmark-extraction/src

rm -r /tmp/ukhack/output/; spark-submit --master local[*]    --executor-memory=8g     --driver-memory=8g    --py-files lib/python-lib.zip    landmark_extractor_cdr2.py    "$data_dir"/$site/train/  /tmp/ukhack/output "$data_dir"/$site/rules.json

train_jl="$site"_extractions_train.jl
cd /tmp/ukhack/output/
mv part-00000 $train_jl
cd "$data_dir"/$site/
mv /tmp/ukhack/output/$train_jl "$data_dir"/$site/extractions/


cd /Users/amandeep/Github/landmark-extraction/src

rm -r /tmp/ukhack/output/; spark-submit --master local[*]    --executor-memory=8g     --driver-memory=8g    --py-files lib/python-lib.zip    landmark_extractor_cdr2.py    "$data_dir"/$site/evaluate/  /tmp/ukhack/output "$data_dir"/$site/rules.json

evaluate_jl="$site"_extractions_evaluate.jl
cd /tmp/ukhack/output/
mv part-00000 $evaluate_jl
cd "$data_dir"/$site/
mv /tmp/ukhack/output/$evaluate_jl "$data_dir"/$site/extractions/
