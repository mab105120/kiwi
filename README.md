
# Assignment 1 Instructions

Please read the following instructions carefully to ensure proper submission and compliance with the application requirements.

## Application requirements

### Console Interaction Guidelines

- As this application is designed as a command-line interface, all user interactions—including data presentation, input collection, and navigation—must occur via the console.
- For enhanced console output and user experience, utilize the open-source [rich](https://rich.readthedocs.io/en/latest/index.html) Python library.
- Menus should be displayed with clearly numbered options. The application should prompt the user to enter the corresponding number for their selection and handle the input appropriately to guide navigation and workflow.

### Login Menu

Upon application startup, the login menu will be displayed in the console, presenting two options:

1. **Login**
2. **Exit**

- Selecting "Exit" will immediately terminate the application. This is the only supported method for exiting the program.
- Selecting "Login" will prompt the user to enter their username and password. The application will validate these credentials against the stored data in the `db` module, which serves as a mock database using in-memory variables and functions to simulate CRUD operations.
- 🚫 If authentication is successful, the user will be granted access to the main menu. Otherwise, an appropriate error message will be displayed.
- The application must maintain a reference to the currently logged-in user. This should be implemented as a dedicated variable in the `db` module, which is set upon successful login and reset to `None` upon logout to support features that require user context.

### Main Menu

Upon successful login, users are presented with the main menu, which offers the following options:

1. **Manage Users** – Accessible only to the admin user, this option enables viewing, adding, or deleting users.
2. **Manage Portfolios** – Allows the logged-in user to view their portfolios, create new portfolios, liquidate investments, or return to the main menu.
3. **Marketplace** – Provides access to view available securities, place purchase orders, or return to the main menu.
4. **Logout** – Logs out the current user and returns to the login menu.

### Main Menu > Manage Users

The "Manage Users" feature is accessible from the main menu. When this option is selected, the application must verify whether the currently logged-in user is the admin.  
🚫 If the user is the admin, the "Manage Users" menu should be displayed. Otherwise, the application should present an error message indicating that the user does not have the necessary authorization to access this feature.

> ### User Object  
>
> The application must define a User class to represent users. The class must have, at least, the following attributes: First name (str), last name (str), username (str), password (str), balance (float).

#### Main Menu > Manage Users > View Users

- This option displays all users registered in the application in a tabular format using the `Table` class from the `rich` library.
- The user list will always include at least one entry, as the application is initialized with a pre-configured admin user.

#### Main Menu > Manage Users > Add User

- This option enables the admin user to add new users to the application.
- The following information must be collected from the admin:

    1. First name: The user's first name.
    2. Last name: The user's last name.
    3. Username: A unique username for the new user.
    4. Password: The user's password.
    5. Balance: The initial investment balance for the user.

- 🚫 Upon receiving this information, the application must verify that the chosen username does not already exist. If the username is not unique, an error message should be displayed.
- Otherwise, the new user should be created, added to the user dictionary in the `db` module, and a confirmation message should be shown indicating successful user creation.

#### Main Menu > Manage Users > Delete User

- This menu allows the logged in admin user to delete any other users from the system.
- When this option is selected, the logged in user is promoted for the username of the user to be deleted.
- 🚫 If the username does not exist, an error message should be printed. Otherwise, the user should be deleted.

⚠️ **Note:** if the user has existing portfolios then the application should not allow deletion of the user. Alternatively, an error message requesting to remove all existing portfolios should be printed.

### Main Menu > Manage Portfolios

When the user chooses the second option in the main menu, the _Manage Portfolio_ menu. The menu has the following options:

1) View portfolios: this option prints the currently logged in user's portfolios with relevant details.
2) Create portfolio: option to create a new portfolio.
3) Delete porfolio: option to delete an existing portfolio.
4) Havest Investment: option to liquidate an investment holding from a portfolio.

> ### Portfolio Object  
>
> The application must define a portfolio class that represents the user portfolio. At a minimum, the portfolio must have the following attributes: id (int), name (str), description (str), and holdings (list[investment]).  
>
> #### Portfolio Holdings  
>
> The portfolio object must have an attribute to store all investments in the portfolio. This shoulld be a list that is initially empty but is modified when the user purchases or liquidates investments. For easier implementation, it is recommended to create a separate class _Investment_ to represent a user investment held in a portfolio.  
>
> _Hint: The porfolio class should have helper methods/functions to add or remove items from the holdings list._
>
> #### Investment Object
>
> The investment object represents an investment held in a portfolio. The object must have, at a minimum, the following attributes: ticker (str), quantity (int), purchase_price (float).

#### Main Menu > Manage Portfolios > View Portfolios

This option should print the logged in user's list of portfolios in a table format (_hint: check out the [table class](https://rich.readthedocs.io/en/latest/tables.html) in the rich library._)  
At a minimum the following portfolio details should be shown in the output:

- Id: the portfolio automatically generated unique id.
- Name: name of the portfolio
- Description: the description of the portfolio.

⚠️ **Note**: the list of portfolios should be limited to the ones owned by the currently logged in user. If the logged in user does not have any portfolios created already, then this option should print a message telling the user that no portfolios exist.

#### Main Menu > Manage Portfolios > Create Portfolio

This option allows the currently logged in user to create a new portfolio. The application must prompt the user for:

- Portfolio name
- Porfolio description

⚠️ **Note**: The user will not provide the porfolio id at the time of creating a new portfolio. This id should be managed by the application and it must be unique for every new portfolio. The id generation should be abstracted away from the user.

#### Main Menu > Manage Portfolios > Delete Portfolio

This option allows the logged in user to delete a portfolio.

- The app should prompt the logged in user for the id of the portfolio that should be deleted.
- 🚫 The app must validate that the provided portfolio id is valid.
- 🚫 The portfolio holdings must be empty before a portfolio can be deleted. If the length of the investments list on the portfolio object is not empty, then an error message should be printed notifying the user that portfolio investments must be liquidated before deleting a portfolio.
- Otherwise the portfolio will be deleted and a confirmation message will be printed to the user.

#### Main Menu > Manage Portfolios > Harvest Investment

This option allows the user to partially or fully liquidate an investment from a portfolio. When this option is selected the user should be prompted for:

- Portfolio id: the id of the portfolio the holds the investment to liquidate.
- Ticker: the ticket of the security to liquidate.
- Quantity: the number of shares to liquidate
  - Partial liquidation: given quantity is less than the total quantity held in the investment.
  - Full liquidation: given quantity is equal to the total quantity held in the investment.
- Sale price: the price to use for liquidating the investment (PS: for current purposes we will allow the user to provide the sale price, a future enhancement to the application will connect the app to a live data source of securities)

🚫 The user should recieve an error message if:

- The portfolio id is invalid
- The investment does not exist on the given portfolio
- The quantity provided exceeds the total quantity in the investment.

Otherwise the liquidation order should go through. After successful liquidation the app must:

- Update the user balance to reflect this transaction (new balance = old balance + sale proceeds)
- Update in the portfolio investment list to reflect the current holdings of the user. In the case of a full liquidation, the investment should be removed from the investments list. Otherwise, the quantity of the investment should be modified accordingly.

### Main Menu > Marketplace

This option allows the user to:

1. View securities: print all securities that are available for investment.
2. Place Buy Order: add an investment to a portfolio.

> ### Security Object  
>
> The application must define a security class that represents the security objects. At a minimum, the class must have the following attributes:
>
> - Ticker (str): a unique identifier for a security.
> - Issuer (str): the company that issued the security.
> - Price (float): the price of the security.

#### Main Menu > Marketplace > View Secuities

This option should print the all securities available for investment in a table format (_hint: check out the [table class](https://rich.readthedocs.io/en/latest/tables.html) in the rich library._)  
At a minimum the following security details should be shown in the output:

- Ticker
- Issuer
- Price

⚠️ **Note:** The list of securities available for investment should be a static list of security objects in the db module. As a developer you are free to include as many securities as you want (3 at a minimum). In later iterations of development, the app will be connected to a live source for security data so that this list is not static.

#### Main Menu > Marketplace > Place Buy Order

This option allows the logged in user to add an investment to an existing portfolio. When the user selected this option, they should be prompted for the following input:

- Portfolio id: the id of the portfolio to add the investment to.
- Ticker: unique identifier of the security to invest in.
- Quantity: number of shares in the buy order.

🚫 The app should throw an error if:

- Potfolio id is invalid.
- Ticker is invalid.
- The buy order amount (price * quantity) exceeds the user's current balance.

Otherwise the buy order should go through. After a successful buy order the app must:

- Adjust the user balance to reflect the buy order amount (new balance = old balance - buy order amount)
- Adjust the portfolio investment holdings
  - If the investment already exists (i.e. the current logged in user already has shares of this security in their portfolio), then quantity of the investment should be adjusted accordingly.
  - If the investment does not exist, a new investment object should be added the list of investment holdings on the portfolio.

## Development Specifications

### Code Organization

The code must be properly organized in modules and packages that make functional and logical sense. Separate modules should be created for specific purposes and imported into other modules when needed. No module should contain functions with diverging responsibilities (e.g., function to add a user and delete a portfolio should not be in the same module).

Code should be organized as follows:

```python
-> root directory
 -> app
  -> cli # package for all console related modules.
  -> domain # pacakge for all class modules (also called /models)
  -> services # pacakage for service modules that contain app logic.
 - main.py # startup module.
 - db.py # module to mock the database
- .gitignore
- requirements.txt
```

### Database

For the purposes of this assignment the database will be mocked using the in the `db` module. This module will act like a database by:

- Storing data in module variables.
- Defining functions to modify data.

#### Stored attributes

- `logged_in_user`: stores the user object of the logged in user.
- `portfolios`: a dictionary to store portfolios by username.
- `securities`: a dictionaty to store securities available for investment.
- `next_portfolio_id`: stores the next id available for next portfolio.

#### Helper functions

The `db` module should expose function to modify data. For example, there should be a function to add/remove users or portfolios. The `db` module should also contain helper functions to assign new unique portfolio ids when the user creates a new portfolio. The implementation details are up to the developer but an easy way to attain this is by defining an int attribute in this module for storing the next available portfolio id. Anytime a new portfolio is created, the current portfolio gets the next id and then the next id attribute is incremented.

### Exception Handling

Exception handling is a fundamental aspect of writing robust and reliable Python code. Just like how a skilled driver navigates through unexpected roadblocks, a proficient programmer gracefully handles exceptions to maintain application stability and provide users with meaningful feedback. See [this](https://medium.com/@saadjamilakhtar/5-best-practices-for-python-exception-handling-5e54b876a20) article for tips on exception handling best practices.

Your application must:

- Never crash - the only way the application should terminate is if the user chooses so.
- Validate user input to ensure data quality.
- Print user friendly errors with meaningful messages. The user should never be confused about why your app is complaining.
- Where suitable, use custom exception classes.
- Handle all exceptions gracefully using try/except blocks.

## Assignment Submission Evaluation

### Pull Request

All code must be committed to a remote branch (e.g., `assignemnt-1`). The assignment is submitted as a pull request from the remote branch to the main branch.

**IMPORTANT** There should be NO CODE committed to the main branch. Remember: code files in the main branch can be modified ONLY using a pull request. This is to ensure that every code is reviewed before it is committed to the main branch.

In order to avoid committing to the main branch accidently follow the steps blow to protect the main branch:

1) Go to your repository on github.com → Settings → Branches.
2) Under "Branch protection rules" click "Add rule".
3) For "Branch name pattern" enter: main
4) Enable the protections you want (recommended set):
    - Require pull request reviews before merging (set required approvers to 1+).
    - Include administrators (check "Include administrators") if you want the rule to also apply to repo admins.
5) Save the rule.

### Evaluation Checklist

Your submission will be evaluated based on:

- Assignment submission: there should be only 1 pull request for the final assignment submission. If you have multiple PRs, name the final one clearly so that the correct PR is evaluated.
- Dependencies: all dependencies must be clearly defined in a dedicated `requirements.txt` file. The application should not require any external libraries that are not defined in this file.
- App execution: the app should run using _only_ the following steps:

    1. Clone remote repository to local development machine.
    2. Create a virtual environment for the cloned respository.
    3. Activate virtual environment.
    4. Install dependencies using the following command `pip install -r requirements.txt`
    5. Runt he application as follows: `py -m main`
- Error handling: The app must never crash. Any errors should be printed with a meaningful message. After an error the user should be routed back to the relevant menu depending on the case.
- Code organization: Code is organized properly following best practice with logically defined modules/packages.
- Hinting: all functions and important variables (e.g., data variables in the `db` module) must be properly hinted. All function parameters and return values should be hinted. See [official docs](https://docs.python.org/3/library/typing.html) for help.

### Grading Rubric

| Criterion | Weight |
| :---------| :-------|
| Functionality & Feature Completion | 40%|
|Code Quality & Organization | 25%|
|Exception Handling & Stability | 15%|
|OOP Design & Data Modeling | 10%|
|Version Control & Submission Compliance | 10%|
