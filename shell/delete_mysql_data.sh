#!/bin/bash

# MySQL连接配置
MYSQL_HOST="localhost"
MYSQL_USER="root"
MYSQL_PASS="password"
MYSQL_DB="your_database"
TABLE_NAME="your_table"

# 删除条件
DELETE_CONDITION="created_at < '2023-01-01'"

# 线程数和批次大小
THREADS=4
BATCH_SIZE=1000

# 获取需要删除的总行数
TOTAL_ROWS=$(mysql -h $MYSQL_HOST -u $MYSQL_USER -p$MYSQL_PASS -D $MYSQL_DB -sN -e "SELECT COUNT(*) FROM $TABLE_NAME WHERE $DELETE_CONDITION")

# 计算总批次数
TOTAL_BATCHES=$(( ($TOTAL_ROWS + $BATCH_SIZE - 1) / $BATCH_SIZE ))

# 删除函数
delete_batch() {
    local start=$1
    local end=$2
    mysql -h $MYSQL_HOST -u $MYSQL_USER -p$MYSQL_PASS -D $MYSQL_DB -e "DELETE FROM $TABLE_NAME WHERE $DELETE_CONDITION LIMIT $BATCH_SIZE"
    echo "Deleted batch $start to $end"
}

# 多线程删除
for ((i=0; i<$TOTAL_BATCHES; i++)); do
    start=$((i * $BATCH_SIZE + 1))
    end=$(( (i + 1) * $BATCH_SIZE ))
    delete_batch $start $end &
    if (( (i + 1) % $THREADS == 0 )); then
        wait
    fi
done

wait
echo "All data deleted successfully!"