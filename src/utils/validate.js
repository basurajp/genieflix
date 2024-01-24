export  const checkValidate  =(email , password)=>{

const isEmailIsValid = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/.test(email)
const isPasswordIsValid = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/.test(password)

if(!isEmailIsValid) return 'Email is not Valid'
if(!isPasswordIsValid) return 'Password is Not Valid '
return null


}