from vm import run

code = '''

function fibonacci(n)
  if n < 2 then
    return n
  else
    return fibonacci(n-1) + fibonacci(n-2)
  end
end

function items(t)
  local c = 0
  for k, v in pairs(t) do
    print(k, '->', v)
    c = c + 1
  end
  print('len =', c)
end

function newCounter ()
    local count = 0
    return function () -- 匿名函数
        count = count + 1
        return count
    end
end

local function max(...)
    local args = {...}
    local val, idx
    for i = 1, #args do
        if val == nil or args[i] > val then
            val, idx = args[i], i
        end
    end
    return val, idx
end

print("Hello, Lua!")
print(fibonacci(16))  -- test function call
items({a=1, b=2, c=3}) -- test table
c1 = newCounter()
c2 = newCounter()
print(c1(), c1(), c2(), c1(), c2()) -- test closure
print(max(1, 100, max(1000, 10)))
'''

run(code)
