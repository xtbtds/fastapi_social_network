# [-14, -9, -4, 0, 1, 3, 7, 10]

# def solution(array: list[int]) -> list[int]:
#     result = [0 for i in array]
#     i = 0
#     j = len(array)-1
#     current = j
#     while i != j and i < len(array) and j >= 0:
#         if array[i] * array[i] > array[j] * array[j]:
#             result[current] = array[i] * array[i]
#             i += 1 
#         else:
#             result[current] = array[j] * array[j]
#             j -= 1 
#         current -= 1
#     return result


# nums = [4,7,15,9,2,-5,3,11], k = 3
from collections import deque
def solution(array: list[int], k) -> list[int]:
    if len(array) < k:
        return None
    d = deque()
    d.append(array[0])
    d.append(array[1])
    d.append(array[2])
    
