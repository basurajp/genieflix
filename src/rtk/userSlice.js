import { createSlice } from "@reduxjs/toolkit";

const userSlice = createSlice({
  name: "user",
  initialState: null,
  reducers: {
    addUser: (state, actiion) => {
      return actiion.payload;
    },
    removeUser: (state, actiion) => {
      return null;
    },
  },
});

export const {addUser ,removeUser} = userSlice.actions


export default userSlice.reducer