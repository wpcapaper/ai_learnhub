# 函数定义

## 什么是函数

函数是一段可重用的代码块，用于执行特定任务。函数可以接受参数，并返回结果。

## 定义函数

在 Python 中，使用 `def` 关键字定义函数：

```python
def greet(name):
    """向指定的人打招呼"""
    message = f"你好，{name}！"
    return message

# 调用函数
result = greet("Alice")
print(result)  # 输出：你好，Alice！
```

## 函数的组成部分

### 1. 函数名

函数名应该使用小写字母和下划线，描述函数的功能：

```python
def calculate_sum():    # 好的函数名
def CalculateSum():    # 不推荐（使用大写）
```

### 2. 参数

参数是函数的输入：

```python
def add_numbers(a, b):
    """计算两个数的和"""
    return a + b

result = add_numbers(10, 20)
print(result)  # 输出：30
```

### 3. 返回值

函数可以使用 `return` 语句返回结果：

```python
def get_circle_area(radius):
    """计算圆的面积"""
    import math
    area = math.pi * radius ** 2
    return area

area = get_circle_area(5)
print(f"半径为 5 的圆的面积是: {area:.2f}")
```

## 默认参数

你可以为参数设置默认值：

```python
def greet(name, greeting="你好"):
    """向指定的人打招呼，使用自定义问候语"""
    return f"{greeting}，{name}！"

print(greet("Bob"))           # 输出：你好，Bob！
print(greet("Bob", "Hi"))     # 输出：Hi，Bob！
```

## 关键字参数

调用函数时，可以使用参数名指定值：

```python
def introduce(name, age, city):
    """介绍一个人的基本信息"""
    return f"{name}，{age}岁，来自{city}"

# 使用关键字参数
print(introduce(name="Alice", city="北京", age=25))
# 输出：Alice，25岁，来自北京
```

## 可变参数

使用 `*args` 和 `**kwargs` 接受任意数量的参数：

```python
def sum_all(*numbers):
    """计算所有数字的和"""
    return sum(numbers)

print(sum_all(1, 2, 3, 4, 5))  # 输出：15

def print_info(**kwargs):
    """打印所有关键字参数"""
    for key, value in kwargs.items():
        print(f"{key}: {value}")

print_info(name="Alice", age=25, city="北京")
# 输出：
# name: Alice
# age: 25
# city: 北京
```

## 匿名函数

匿名函数使用 `lambda` 关键字定义：

```python
# 普通函数
def square(x):
    return x * x

# 匿名函数
square_lambda = lambda x: x * x

print(square(5))          # 输出：25
print(square_lambda(5))     # 输出：25
```

## 函数文档字符串

函数的第一行通常是一个文档字符串（docstring），用于描述函数的功能：

```python
def calculate_triangle_area(base, height):
    """
    计算三角形的面积

    Args:
        base (float): 三角形的底边长
        height (float): 三角形的高

    Returns:
        float: 三角形的面积

    Example:
        >>> calculate_triangle_area(10, 5)
        25.0
    """
    return 0.5 * base * height
```

## 递归函数

函数可以调用自身，这称为递归：

```python
def factorial(n):
    """计算 n 的阶乘"""
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(factorial(5))  # 输出：120 (5 * 4 * 3 * 2 * 1)
```

## 练习

尝试编写以下函数：

```python
# 练习 1：写一个函数计算矩形面积
def rectangle_area(width, height):
    """在此编写你的代码"""
    pass

# 练习 2：写一个函数判断数字是否为偶数
def is_even(number):
    """在此编写你的代码"""
    pass

# 测试你的函数
print(f"矩形面积: {rectangle_area(10, 5)}")
print(f"4 是否为偶数: {is_even(4)}")
print(f"3 是否为偶数: {is_even(3)}")
```

## 总结

本章我们学习了：
- 如何定义函数
- 函数的组成部分（函数名、参数、返回值）
- 默认参数和关键字参数
- 可变参数（*args 和 **kwargs）
- 匿名函数（lambda）
- 函数文档字符串
- 递归函数

恭喜你完成了 Python 基础入门课程的学习！你现在已经掌握了 Python 的基础知识，可以开始编写简单的程序了。

继续加油！
