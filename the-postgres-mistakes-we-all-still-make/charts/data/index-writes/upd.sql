\set id random(1, 1000000)
UPDATE idxcost SET a = a + 1 WHERE id = :id;
