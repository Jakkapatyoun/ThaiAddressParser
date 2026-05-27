# Knowledge Base — Download Parts

ไฟล์ `address_knowledge.db` ถูก compress เป็น `.gz` แล้ว split เป็น 7 parts

## วิธี Download และ Assemble บน Windows

### 1. ดาวน์โหลดทั้ง 7 parts มาไว้ใน folder เดียวกัน
```
address_knowledge.db.gz.part_aa  (80 MB)
address_knowledge.db.gz.part_ab  (80 MB)
address_knowledge.db.gz.part_ac  (80 MB)
address_knowledge.db.gz.part_ad  (80 MB)
address_knowledge.db.gz.part_ae  (80 MB)
address_knowledge.db.gz.part_af  (80 MB)
address_knowledge.db.gz.part_ag  (2.4 MB)
```

### 2. เปิด Command Prompt ใน folder นั้น แล้วรัน:
```cmd
copy /b part_aa+part_ab+part_ac+part_ad+part_ae+part_af+part_ag address_knowledge.db.gz
```

### 3. Extract .gz ด้วย 7-Zip หรือ Windows 11 built-in:
```
คลิกขวา address_knowledge.db.gz → Extract Here
```
จะได้ `address_knowledge.db` ขนาด ~2 GB

### 4. วาง DB ที่:
```
%USERPROFILE%\Documents\ThaiAddressParser\data\address_knowledge.db
```
