import { sum } from "../sum";

test("sum function should calulate sum of number ", () => {
  const res = sum(2, 5);

  expect(res).toBe(7); //  this is line is known asasseration 
});
