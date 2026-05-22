-- Idempotent seed for E2E. Items + recipes used by all specs.
INSERT INTO item (id, name, category, grade, current_price, last_price_at, created_at, updated_at)
VALUES
  (9001, 'E2E Leaf Item', 'OTHER', 'BASIC', 100, NULL, NOW(), NOW()),
  (9002, 'E2E Mid Item',  'CRAFTING', 'BASIC', 500, NULL, NOW(), NOW()),
  (9003, 'E2E Top Item',  'CRAFTING', 'BASIC', 2000, NULL, NOW(), NOW())
ON CONFLICT (id) DO UPDATE
  SET current_price = EXCLUDED.current_price;

INSERT INTO recipe (id, item_id, output_qty)
VALUES
  (9101, 9002, 1),
  (9102, 9003, 1)
ON CONFLICT (id) DO NOTHING;

INSERT INTO recipeingredient (id, recipe_id, ingredient_item_id, quantity)
VALUES
  (9201, 9101, 9001, 5),
  (9202, 9102, 9002, 3)
ON CONFLICT (id) DO NOTHING;
