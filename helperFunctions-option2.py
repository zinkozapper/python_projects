
def revString(str):
	netstr = ''
	for i in range(len(str)-1, -1, -1):
		netstr += str[i]
	print(netstr)

def maxThreeInts(a, b, c):
	print(max(a,b,c))


def factorial(inp):
	if inp == 0:
		return 1
	else:
		return inp * factorial(inp-1)



def fibonacci(inp):
	counter1 = 0
	counter2 = 1
	for i in range(0,inp):
		counter1 = counter1 + counter2
		counter2 = counter1 - counter2
	print(counter1)

def userChoice(inp):
	if inp == 1:
		fibonacci(int(input("Please enter how many iterations of the Fibonacci sequence you want to check: ")))
	if inp == 2:
		revString(str(input("Please enter a string to be reversed: ")))
	if inp == 3:
		print("Please enter 3 integers seperated by spaces to find the greatest")
		inp = list(map(int, input().split()))
		maxThreeInts(inp[0], inp[1], inp[2])
	if inp == 4:
		facResult = factorial(int(input("Please enter a interger to find it's factorial: ")))
		print(facResult)

def userPrompt():#Choices for user running program
	print("Please call a function: ")
	print("1) Fibonacci")
	print("2) Reverse String")
	print("3) Max of integers")
	print("4) Factorial")
	userChoice(int(input()))
	

def main(): 
	userPrompt()


if __name__ == '__main__':
	main()
