#!/bin/bash
# 将 citywalk_mongo.archive 导入到远端 MongoDB
# 用法: bash scripts/restore_mongo.sh

set -e

ARCHIVE_FILE="$(dirname "$0")/../citywalk_mongo.archive"
MONGO_URI="mongodb://smart:smart-hv77y27fjdd4@10.7.0.14:27017"
DB_NAME="citywalk"

if [ ! -f "$ARCHIVE_FILE" ]; then
  echo "❌ 找不到归档文件: $ARCHIVE_FILE"
  exit 1
fi

echo "📦 开始导入 MongoDB 数据..."
echo "   目标: ${MONGO_URI}/${DB_NAME}"
echo "   文件: $(ls -lh "$ARCHIVE_FILE" | awk '{print $5}')"
echo ""

mongorestore \
  --uri="${MONGO_URI}" \
  --archive="$ARCHIVE_FILE" \
  --db="$DB_NAME" \
  --nsInclude="citywalk.*"

echo ""
echo "✅ 导入完成！验证数据..."
mongosh "${MONGO_URI}/${DB_NAME}" --quiet --eval "
  const cols = db.getCollectionNames();
  print('集合: ' + cols.join(', '));
  cols.forEach(c => print('  ' + c + ': ' + db[c].countDocuments({}) + ' 条'));
"
