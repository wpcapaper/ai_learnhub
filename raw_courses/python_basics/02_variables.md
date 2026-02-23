# 变量与数据类型

## 什么是变量

变量是程序中用来存储数据的容器。在 Python 中，你不需要提前声明变量的类型。

## 定义变量

```python
# 定义变量并赋值
name = "Alice"
age = 25
height = 1.65
is_student = True

# 打印变量
print(f"姓名: {name}")
print(f"年龄: {age}")
print(f"身高: {height}m")
print(f"是学生: {is_student}")
```

## 基本数据类型

Python 有以下基本数据类型：

### 1. 字符串（String）

字符串用单引号或双引号包围：

```python
greeting = "你好"
message = '欢迎学习 Python'
```

### 2. 整数（Integer）

整数是不带小数点的数字：

```python
count = 42
year = 2024
```

### 3. 浮点数（Float）

浮点数是带小数点的数字：

```python
price = 19.99
pi = 3.14159
```

### 4. 布尔值（Boolean）

布尔值只有两个：True 或 False：

```python
is_active = True
is_deleted = False
```

## 类型转换

你可以使用内置函数进行类型转换：

```python
# 字符串转整数
x = int("42")  # x = 42

# 整数转字符串
y = str(100)  # y = "100"

# 浮点数转整数
z = int(3.99)  # z = 3
```

## 变量命名规则

- 变量名只能包含字母、数字和下划线
- 变量名不能以数字开头
- 变量名区分大小写（myVar 和 myvar 是不同的）
- 不要使用 Python 关键字作为变量名

```python
# 合法的变量名
my_name = "Alice"
user_age = 25
_private_var = "secret"

# 非法的变量名
2nd_name = "Bob"  # 不能以数字开头
class = "Math"  # class 是 Python 关键字
```

## 动态类型

Python 是动态类型语言，这意味着变量可以随时改变类型：

```python
x = 10      # x 是整数
x = "Hello" # x 现在是字符串
x = 3.14    # x 现在是浮点数
```

## 练习

尝试编写以下代码：

```python
# 练习 1：定义一个变量存储你的名字
your_name = "在这里填写你的名字"

# 练习 2：定义一个变量存储你的年龄
your_age = 0  # 在这里填写你的年龄

# 练习 3：计算 10 年后你的年龄
age_in_10_years = your_age + 10

# 打印结果
print(f"你的名字是: {your_name}")
print(f"你的年龄是: {your_age}")
print(f"10 年后你的年龄是: {age_in_10_years}")
```

## 总结

本章我们学习了：
- 什么是变量
- Python 的基本数据类型（字符串、整数、浮点数、布尔值）
- 如何进行类型转换
- 变量命名规则
- Python 的动态类型特性

在下一章中，我们将学习如何定义和使用函数。
