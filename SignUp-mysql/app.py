from flask import Flask, render_template, url_for, flash, redirect,request
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager,UserMixin,login_user, current_user, logout_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo,ValidationError
from flask import Flask, request, render_template, redirect, url_for
from decouple import config
from flask import Flask, request, render_template
import os
import subprocess
import random
import base64

app = Flask(__name__, static_url_path='/static')

app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'

# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quelin.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://aayush:Aayush8368*@localhost/newdatabase'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'



class User(db.Model,UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    cockpitform = db.relationship('cockpitform', backref='items', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"


class cockpitform(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200))
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.now)
    complete=db.Column(db.Boolean,default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"cockpitform('{self.content}', '{self.date_posted}')"

class RegistrationForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(),Length(min=3, max=20)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('username already exist. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('email already exist. Please choose a different one.')
   
class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html')

@app.route('/cloud')
def cloud():
    return render_template('cloud.html')


@app.route('/aws')
def aws():
    return render_template('aws.html')

@app.route('/submit_form', methods=['POST'])
def submit_form_aws():
# Get  AWS form data
    Access_key = request.form.get('Access_key')
    secret_Access_key = request.form.get('secret_Access_key')
    User_name = request.form.get('User_name')
    User_Id = str(int(random.random()))



    # Write AWS form data to terraform.vars file
    with open('terraform.tfvars', 'w') as f:
        f.write(f'Access_key = "{Access_key}"\n')
        f.write(f'secret_Access_key = "{secret_Access_key}"\n')
    

     ## starting the script

    # Azure Resource Group and Key Vault Configuration
    resource_group_name = "prashant-rg"  
    key_vault_name = User_name + User_Id  
    secrets_file_path = "./terraform.tfvars"

    

    # Replace underscores with hyphens in the Key Vault and Resource Group names
    key_vault_name = key_vault_name.replace("_", "-")
    resource_group_name = resource_group_name.replace("_", "-")

    

    # Read secrets from the file
    secrets = {}
    with open(secrets_file_path, "r") as file:
        for line in file:
            key, value = line.strip().split(" = ")
            secrets[key] = value

    

    # Authenticate to Azure
    try:
        # Use Azure CLI to get the access token
        access_token = subprocess.check_output(["az", "account", "get-access-token", "--query", "accessToken", "-o", "tsv"]).decode("utf-8").strip()
    except subprocess.CalledProcessError:
        print("Error: Failed to obtain Azure access token. Make sure you are logged into Azure CLI.")
        exit(1)


    # Create Azure Key Vault in the specified Resource Group
    try:
        subprocess.check_call(["az", "keyvault", "create", "--name", key_vault_name, "--resource-group", resource_group_name, "--location", "southcentralus"])
        print(f"Azure Key Vault '{key_vault_name}' created successfully in Resource Group '{resource_group_name}'.")
    except subprocess.CalledProcessError:
        print(f"Azure Key Vault '{key_vault_name}' already exists or encountered an error during creation in Resource Group '{resource_group_name}'.")

    

    # Store secrets in Azure Key Vault
    for key, value in secrets.items():
        # Replace underscores with hyphens in the secret name
        key = key.replace("_", "-")
        encoded_value = base64.b64encode(value.encode("utf-8")).decode("utf-8")     
        command = f"az keyvault secret set --vault-name {key_vault_name} --name {key} --value {encoded_value} --output none --query 'value'"
        # command = f"az keyvault secret set --vault-name {key_vault_name} --name {key} --value {value} --output none --query 'value'"

    

        try:
            # Use Azure CLI to set the secret in the Key Vault
            subprocess.check_call(["bash", "-c", f'AZURE_ACCESS_TOKEN="{access_token}" {command}'])
            print(f"Secret '{key}' stored in Azure Key Vault '{key_vault_name}' successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error: Failed to store secret '{key}' in Azure Key Vault '{key_vault_name}'.")
            print(e)

    

    print("All secrets have been stored in Azure Key Vault.")
    

    os.remove(secrets_file_path)     
    

    with open(secrets_file_path, "w"):         pass 

    ## ending the script
    flash('Credential Added Successfully', 'success')

    return render_template('./create_aws.html')

@app.route('/aws_form', methods=['GET'])
def aws_form():
    return render_template('create_aws.html')

@app.route('/create_aws_form', methods=['GET'])
def create_aws_form():
    return render_template('create_aws.html')

@app.route('/success', methods=['GET'])
def success_aws():
    return render_template('success.html')

@app.route('/create_aws', methods=['POST'])
def create_aws():
    # Retrieve form data
    resource_group = request.form.get('resource_group')
    Region = request.form.get('Region')
    availability_zone = request.form.get('availability_zone')
    eks_name = request.form.get('eks_name')
    eks_version = request.form.get('eks_version')
    node_count = request.form.get('node_count')
    cluster_type = request.form.get('cluster_type')
    
    eks_version = float(eks_version)

    # Initialize variables for vm_name and vm_pass
    vm_name = None
    vm_pass = None

    # Process form data based on Cluster Type
    if cluster_type == 'Private':
        vm_name = request.form.get('vm_name')
        vm_pass = request.form.get('vm_pass')


    # Create the content for terraform.tfvars
    with open('terraform.tfvars', 'w') as f:
        f.write(f'resource_group = "{resource_group}"\n')
        f.write(f'Region = "{Region}"\n')
        f.write(f'availability_zone = "{availability_zone}"\n')
        f.write(f'eks_name = "{eks_name}"\n') 
        f.write(f'eks_version = "{eks_version}"\n')
        f.write(f'node_count = "{node_count}"\n')
        f.write(f'cluster_type = "{cluster_type}"\n')
        if vm_name is not None:
            f.write(f'vm_name = "{vm_name}"\n')
            f.write(f'vm_pass = "{vm_pass}"\n')

    # You can also redirect the user to a success page if needed
    
    return render_template('success.html')

#azure form
@app.route('/azure')
def azure():
    return render_template('azure.html')

@app.route('/submit_form_azure', methods=['POST'])
def submit_form_azure():
    # Get  azure form data
    subscription_id = request.form.get('subscription_id')
    client_id = request.form.get('client_id')
    client_secret = request.form.get('client_secret')
    tenant_id = request.form.get('tenant_id')
    User_name = request.form.get('User_name')
    User_Id = str(int(random.random()))
 
    # Write Azure form data to terraform.vars file
    with open('terraform.tfvars', 'w') as f:
        f.write(f'subscription_id = "{subscription_id}"\n')
        f.write(f'client_id = "{client_id}"\n')
        f.write(f'client_secret = "{client_secret}"\n')
        f.write(f'tenant_id = "{tenant_id}"\n')
   
    ## starting the script

    # Azure Resource Group and Key Vault Configuration
    resource_group_name = "prashant-rg"  
    key_vault_name = User_name + User_Id  
    secrets_file_path = "./terraform.tfvars"


   # Replace underscores with hyphens in the Key Vault and Resource Group names
    key_vault_name = key_vault_name.replace("_", "-")
    resource_group_name = resource_group_name.replace("_", "-")    

    # Read secrets from the file
    secrets = {}
    with open(secrets_file_path, "r") as file:
        for line in file:
            key, value = line.strip().split(" = ")
            secrets[key] = value

    # Authenticate to Azure
    try:
        # Use Azure CLI to get the access token
        access_token = subprocess.check_output(["az", "account", "get-access-token", "--query", "accessToken", "-o", "tsv"]).decode("utf-8").strip()
    except subprocess.CalledProcessError:
        print("Error: Failed to obtain Azure access token. Make sure you are logged into Azure CLI.")
        exit(1)

    # Create Azure Key Vault in the specified Resource Group
    try:
        subprocess.check_call(["az", "keyvault", "create", "--name", key_vault_name, "--resource-group", resource_group_name, "--location", "southcentralus"])
        print(f"Azure Key Vault '{key_vault_name}' created successfully in Resource Group '{resource_group_name}'.")
    except subprocess.CalledProcessError:
        print(f"Azure Key Vault '{key_vault_name}' already exists or encountered an error during creation in Resource Group '{resource_group_name}'.")

    
    # Store secrets in Azure Key Vault
    for key, value in secrets.items():
        # Replace underscores with hyphens in the secret name
        key = key.replace("_", "-")
        encoded_value = base64.b64encode(value.encode("utf-8")).decode("utf-8")     
        command = f"az keyvault secret set --vault-name {key_vault_name} --name {key} --value {encoded_value} --output none --query 'value'"
        # command = f"az keyvault secret set --vault-name {key_vault_name} --name {key} --value {value} --output none --query 'value'"

        try:
            # Use Azure CLI to set the secret in the Key Vault
            subprocess.check_call(["bash", "-c", f'AZURE_ACCESS_TOKEN="{access_token}" {command}'])
            print(f"Secret '{key}' stored in Azure Key Vault '{key_vault_name}' successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error: Failed to store secret '{key}' in Azure Key Vault '{key_vault_name}'.")
            print(e)

    
    print("All secrets have been stored in Azure Key Vault.")
    
    os.remove(secrets_file_path)     
    
    with open(secrets_file_path, "w"):         pass 
    
    ## ending the script
    flash('Credential Added Successfully', 'success')
    return render_template('create_aks.html')


@app.route('/azure_form', methods=['GET'])
def azure_form():
    return render_template('create_aks.html')

@app.route('/create_aks_form', methods=['GET'])
def create_aks_form():
    return render_template('create_aks.html')

@app.route('/success', methods=['GET'])
def success_aks():
    return render_template('success.html')

@app.route('/create_aks', methods=['POST'])
def create_aks():
    # Retrieve form data
    resource_group = request.form.get('resource_group')
    Region = request.form.get('Region')
    availability_zone = request.form.getlist('availability_zones[]')
    aks_name = request.form.get('aks_name')
    aks_version = request.form.get('aks_version')
    node_count = request.form.get('node_count')
    cluster_type = request.form.get('cluster_type')
    
    aks_version = float(aks_version)
    availability_zone = [f"{zone}" for zone in availability_zone]

    # Initialize variables for vm_name and vm_pass
    vm_name = None
    vm_pass = None

    # Process form data based on Cluster Type
    if cluster_type == 'Private':
        vm_name = request.form.get('vm_name')
        vm_pass = request.form.get('vm_pass')


    # Create the content for terraform.tfvars
    with open('terraform.tfvars', 'w') as f:
        f.write(f'resource_group = "{resource_group}"\n')
        f.write(f'Region = "{Region}"\n')
        f.write(f'availability_zone = "{availability_zone}"\n')
        f.write(f'aks_name = "{aks_name}"\n') 
        f.write(f'aks_version = "{aks_version}"\n')
        f.write(f'node_count = "{node_count}"\n')
        f.write(f'cluster_type = "{cluster_type}"\n')
        if vm_name is not None:
            f.write(f'vm_name = "{vm_name}"\n')
            f.write(f'vm_pass = "{vm_pass}"\n')

    # You can also redirect the user to a success page if needed
    return render_template('success.html')


@app.route('/gcp')
def gcp():
    return render_template('gcp.html')

@app.route('/submit_form_gke', methods=['POST'])
def submit_form_gcp():
    # Check if a file was uploaded
    if 'jsonFile' not in request.files:
        return 'No file part'

    json_file = request.files['jsonFile']

    # Check if the file has a filename
    if json_file.filename == '':
        return render_template('./file_submit.html')

    # Check if the file is a JSON file
    if not json_file.filename.endswith('.json'):
        return render_template('./file_submit.html')
    


    # Specify the directory where you want to save the JSON file
    save_directory = './'

    # Save the JSON file with its original filename
    json_file.save(f"{save_directory}/{json_file.filename}")



    User_name = request.form.get('User_name')
    User_Id = str(int(random.random()))

    # Azure Key Vault and Secrets Configuration
    key_vault_name = User_name + User_Id
    resource_group_name = "prashant-rg"
    location = "westus2"
    secrets_file_path = json_file.filename
        

        # Create Azure Key Vault if it doesn't exist
    create_kv_command = f"az keyvault create --name {key_vault_name} --resource-group {resource_group_name} --location {location}"
    try:
            subprocess.check_output(create_kv_command, shell=True)
            print(f"Azure Key Vault '{key_vault_name}' created successfully in Resource Group '{resource_group_name}'.")
    except subprocess.CalledProcessError:
            print(f"Error: Failed to create Azure Key Vault.")
            exit(1)

        

        # Authenticate to Azure
    try:
            # Use Azure CLI to get the access token
            access_token = subprocess.check_output(["az", "account", "get-access-token", "--query", "accessToken", "-o", "tsv"]).decode("utf-8").strip()
    except subprocess.CalledProcessError:
            print("Error: Failed to obtain Azure access token. Make sure you are logged into Azure CLI.")
            exit(1)

        

        # Read the entire content of the JSON file
    with open(secrets_file_path, 'r') as json_file:
            secrets_content = json_file.read()

        

        # Store the entire JSON content as a secret
    secret_name = "your-secret-name"
    encoded_value = base64.b64encode(secrets_content.encode("utf-8")).decode("utf-8")     
    command = f"az keyvault secret set --vault-name {key_vault_name} --name {secret_name} --value {encoded_value} --output none --query 'value'"
          # Replace with your desired secret name
    # command = f"az keyvault secret set --vault-name {key_vault_name} --name {secret_name} --value '{secrets_content}' --output none --query 'value'"
    try:
            # Use Azure CLI to set the secret in the Key Vault
            subprocess.check_call(["bash", "-c", f'AZURE_ACCESS_TOKEN="{access_token}" {command}'])
            print(f"Secret '{secret_name}' has been stored in Azure Key Vault.")
    except subprocess.CalledProcessError as e:
            print(f"Error: Failed to store secret '{secret_name}' in Azure Key Vault.")
            print(e)

        

    print("Secret has been stored in Azure Key Vault.")
    os.remove(secrets_file_path)    

    
    flash('Credential Added Successfully', 'success')
    return render_template('create_gke.html')
    
#gcp
@app.route('/gcp_form', methods=['GET'])
def gcp_form():
    return render_template('create_gke.html')

@app.route('/create_gke_form', methods=['GET'])
def create_gke_form():
    return render_template('create_gke.html')

@app.route('/success', methods=['GET'])
def success_gke():
    return render_template('success.html')

@app.route('/create_gke', methods=['POST'])
def create_gke():
    # Retrieve form data
    resource_group = request.form.get('resource_group')
    Region = request.form.get('Region')
    availability_zone = request.form.get('availability_zone')
    gke_name = request.form.get('gke_name')
    gke_version = request.form.get('gke_version')
    node_count = request.form.get('node_count')
    cluster_type = request.form.get('cluster_type')
    
    gke_version = float(gke_version)

    # Initialize variables for vm_name and vm_pass
    vm_name = None
    vm_pass = None

    # Process form data based on Cluster Type
    if cluster_type == 'Private':
        vm_name = request.form.get('vm_name')
        vm_pass = request.form.get('vm_pass')


    # Create the content for terraform.tfvars
    with open('terraform.tfvars', 'w') as f:
        f.write(f'resource_group = "{resource_group}"\n')
        f.write(f'Region = "{Region}"\n')
        f.write(f'availability_zone = "{availability_zone}"\n')
        f.write(f'gke_name = "{gke_name}"\n') 
        f.write(f'gke_version = "{gke_version}"\n')
        f.write(f'node_count = "{node_count}"\n')
        f.write(f'cluster_type = "{cluster_type}"\n')
        if vm_name is not None:
            f.write(f'vm_name = "{vm_name}"\n')
            f.write(f'vm_pass = "{vm_pass}"\n')

    # You can also redirect the user to a success page if needed
    return render_template('success.html')


@app.route("/index")
@login_required
def index():
    cockpitforms=cockpitform.query.filter_by(user_id=current_user.id)
    return render_template('index.html',cockpitforms=cockpitforms)


@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('cloud'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Login successful.', 'success')
            return redirect(next_page) if next_page else redirect(url_for('cloud'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    flash('Logout successful.', 'success')
    return redirect(url_for('home'))




@app.route("/account")
@login_required
def account():
    
    return render_template('account.html', title='Account')

@app.route("/add",methods=["POST"])
@login_required
def add():
    user_id=current_user.id
    if request.form['formitem'] != "" :
        cockpitforms=cockpitform(content=request.form['formitem'],complete=False,user_id=user_id)
        db.session.add(cockpitforms)
        db.session.commit()
    else:
        flash('cannot add empty list', 'danger')
        return redirect(url_for("index"))
        
    return redirect(url_for("index"))


@app.route("/complete/<int:id>")
@login_required
def complete(id):
    Form= cockpitform.query.get(id)

    if not Form:
        return redirect("/index")

    if Form.complete:
        Form.complete=False
    else:
        Form.complete=True

    db.session.add(Form)
    db.session.commit()
    
    return redirect("/index")

@app.route("/delete/<int:id>")
@login_required
def delete(id):
    Form=cockpitform.query.get(id)
    if not Form:
        return redirect("/index")
    
    db.session.delete(Form)
    db.session.commit()

    return redirect("/index")


if __name__ == '__main__':
    app.run()