# Neural Network Rules and Architecture

## Input and output

As discussed in the [project readme](../README.md), metrics such as profits, stock price, and growth are key indicators of the success of a private corporation. Because nonprofit organizations cannot earn profits, success must be measured differently for them. A nonprofit must invest any excess earnings back into the organization itself. In this way, we expect successful nonprofits to grow over time. We can measure this growth by looking at tax-data such as total revenue. Revenue should increase from year to year as the organization grows and can provide more services and programs.

The goal of this project is to predict a nonprofit's growth based on their previous decisions. In this way, our neural network takes as input the data from an organization's previous 990 tax form and outputs a prediction for the total revenue as reported on the current year's tax form. In this project, any data included on a nonprofit's tax form may be included as input for the neural network.

One interesting neural network input variable to consider is the value of the year under consideration. Training on data which includes this piece of information should make the neural network stronger. For example, if there was a broad economic slowdown during a particular year-long period, one would expect this to impact nonprofit revenues. If our neural network trained with data which included the value of the year, it could *see* the pervasive effect of the slowdown and learn to associate the year with a decrease in revenues in many nonprofit organizations.

Viewing this project as an interesting application of neural networks, we can include the value of the year (represented as a one-hot vector) as part of the input data in order to make the predictions more accurate. However, viewing this project as a prototype that can be used to help nonprofits predict future revenues based on current budgetary decisions, the year must be excluded from the input -- a neural network has no knowledge of future economic developments. Without access to nonprofit information during a future year, this piece of data would not hold any information for the prediction. Moreover, if the neural network has never trained with a certain piece of input information (such as a one-hot vector with a particular bit in *on* position), the neural network will simply rely on the random transition weights used during the initialization of the neural network causing errors.

In this project, I've chosen to include a representation of the year under consideration as input. It could easily be removed and the network retrained if production-ready code was sought.



## Pre-processing
The data in data.csv takes on a variety of forms. Much of this data needs to be processed before feeding it into a neural network. Processing includes:
- outliers
- exploration
- transforma
- normalize
- reformat ...

## Architecture